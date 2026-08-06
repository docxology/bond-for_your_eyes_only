"""ATAC targeting-communicator escrow/recovery protocol.

The ATAC (Automatic Targeting Attack Communicator) is the mission's lost-key
device. Its cryptographic key must never sit in one place: it is *escrowed* —
split into shares held by separate custodians such that no single custodian
can release it, and the device can be recovered only when a quorum agrees.

This module implements a deterministic key-escrow and recovery protocol built
on real mathematics:

* **Shamir secret sharing** over a prime field ``GF(p)`` — the ATAC key is a
  field element ``s``; we sample a random polynomial of degree ``k-1`` with
  constant term ``s`` and hand each custodian one point ``(x_i, y_i)``. Any
  ``k`` of the ``n`` points reconstruct ``s`` by Lagrange interpolation, while
  fewer than ``k`` points give no information about the key.
* **Share commitment** — each share is committed as ``g^{y_i} mod p`` (where
  ``g`` is a primitive root) so any party can *verify* a share was not
  tampered with during custody without needing the secret.
* **Custody chain** — a hash-chained ledger of handoffs. Each transfer records
  ``(index, from, to, prev_hash)`` and the whole chain is bound together via
  SHA-256, so custody is auditable and append-only.
* **Release** — recovery reconstructs the key from a verified quorum of
  shares and confirms it reproduces the escrowed key fingerprint.

Everything is deterministic: the RNG is fixed-seed, the field is fixed, and no
wall-clock time appears in any persisted artifact.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Sequence

__all__ = [
    "KEY_BOUND",
    "PRIME",
    "PRIMITIVE_ROOT",
    "CustodyTransfer",
    "EscrowError",
    "EscrowState",
    "commit_share",
    "create_escrow",
    "custody_chain_for",
    "custody_chain_hash",
    "custody_chain_is_consistent",
    "generate_custody_transfer",
    "mod_inverse",
    "recover_key",
    "release_key",
    "split_key",
    "verify_share",
]

#: A 61-bit Mersenne prime; large enough for our key space and convenient for
#: deterministic modular arithmetic. Fixed so outputs are reproducible.
PRIME = 2**61 - 1
#: A primitive root modulo ``PRIME`` (used for share commitments).
PRIMITIVE_ROOT = 2

#: Exclusive upper bound for a synthesised ATAC key. Callers deriving a key
#: from a seed draw from ``[1, KEY_BOUND)`` so keys stay well inside the field.
KEY_BOUND = 2**32


class EscrowError(ValueError):
    """Raised for invalid escrow operations (bad quorum, tampered share)."""


@dataclass(frozen=True)
class CustodyTransfer:
    """A single auditable handoff of a share within the custody chain.

    ``index`` is a deterministic monotonic sequence number (position in the
    chain), ``prev_hash`` links the transfer to the one before it, and
    ``chain_hash`` is the commitment binding this record.
    """

    index: int
    from_holder: str
    to_holder: str
    prev_hash: str = ""
    chain_hash: str = ""

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("CustodyTransfer.index must be >= 0")


@dataclass(frozen=True)
class EscrowState:
    """The full escrow: key fingerprint, quorum, shares, commitments, chain.

    All fields are immutable after creation. The shares themselves are held
    by the escrow for simulation/recovery; ``commitments`` let any party
    verify a share without revealing it.
    """

    key_fingerprint: str
    threshold: int
    num_shares: int
    prime: int
    shares: tuple[tuple[int, int], ...]
    commitments: tuple[int, ...]
    custodian_labels: tuple[str, ...]
    custody_chain: tuple[CustodyTransfer, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.threshold < 2:
            raise ValueError("EscrowState.threshold must be >= 2 (a single custodian cannot be a quorum)")
        if not (self.threshold <= self.num_shares <= len(self.shares)):
            raise ValueError("EscrowState.threshold/num_shares inconsistent with shares")
        if not (self.threshold <= len(self.commitments)):
            raise ValueError("EscrowState.commitments must cover at least threshold shares")


# --------------------------------------------------------------------------- #
# Modular arithmetic
# --------------------------------------------------------------------------- #


def _egcd(a: int, b: int) -> tuple[int, int, int]:
    if b == 0:
        return (a, 1, 0)
    g, x1, y1 = _egcd(b, a % b)
    return (g, y1, x1 - (a // b) * y1)


def mod_inverse(a: int, p: int) -> int:
    """Return the modular inverse of ``a`` modulo prime ``p`` (extended Euclid).

    Raises :class:`EscrowError` when ``a`` is not invertible (``a % p == 0``).
    """
    a = a % p
    if a == 0:
        raise EscrowError("modular inverse of 0 is undefined")
    g, x, _ = _egcd(a, p)
    if g != 1:
        raise EscrowError(f"{a} is not invertible modulo {p}")
    return x % p


def _mod_pow(base: int, exp: int, p: int) -> int:
    return pow(base, exp, p)


def _lagrange_interpolate(points: Sequence[tuple[int, int]], x: int, p: int) -> int:
    """Evaluate the interpolation polynomial at ``x`` over ``GF(p)``.

    ``points`` are ``(x_i, y_i)`` shares; with ``k`` distinct points this
    reconstructs the unique degree ``k-1`` polynomial, and at ``x = 0``
    returns the constant term — the escrowed key.
    """
    result = 0
    n = len(points)
    for i in range(n):
        xi, yi = points[i]
        num = 1 % p
        den = 1 % p
        for j in range(n):
            if i == j:
                continue
            xj, _ = points[j]
            num = (num * (x - xj)) % p
            den = (den * (xi - xj)) % p
        term = (yi * num % p) * mod_inverse(den, p) % p
        result = (result + term) % p
    return result


# --------------------------------------------------------------------------- #
# Key / share generation
# --------------------------------------------------------------------------- #


def split_key(
    key: int,
    threshold: int,
    num_shares: int,
    *,
    prime: int = PRIME,
    seed: int = 0,
) -> tuple[tuple[int, int], ...]:
    """Deterministically split ``key`` into ``num_shares`` using Shamir's scheme.

    Args:
        key: The secret (a positive field element < ``prime``).
        threshold: Number of shares required to reconstruct (``k``).
        num_shares: Total number of shares to emit (``n >= k``).
        prime: The field modulus (default :data:`PRIME`).
        seed: Fixed RNG seed (deterministic).

    Returns:
        ``num_shares`` points ``(x, y)`` over ``GF(prime)``.

    Raises:
        EscrowError: if inputs are inconsistent.
    """
    if not (0 < key < prime):
        raise EscrowError(f"key must be in (0, {prime})")
    if not (2 <= threshold <= num_shares):
        raise EscrowError(f"need 2 <= threshold({threshold}) <= num_shares({num_shares})")
    rng = random.Random(seed)
    # polynomial coefficients: a_0 = key, a_1..a_{k-1} random in GF(p)
    coeffs = [key % prime] + [rng.randrange(1, prime) for _ in range(threshold - 1)]
    shares: list[tuple[int, int]] = []
    used_x: set[int] = set()
    while len(shares) < num_shares:
        x = rng.randrange(1, prime)
        if x in used_x:
            continue
        used_x.add(x)
        y = 0
        for power, coeff in enumerate(coeffs):
            y = (y + coeff * _mod_pow(x, power, prime)) % prime
        shares.append((x, y))
    return tuple(shares)


def commit_share(share: tuple[int, int], *, prime: int = PRIME, g: int = PRIMITIVE_ROOT) -> int:
    """Return the public commitment ``g^{y} mod p`` for a share ``(x, y)``.

    Committing stops custody tampering: a party holding a claimed share can be
    checked against the commitment without revealing anything beyond the
    share itself, and the escrow's fingerprint cannot be inferred from
    commitments alone.
    """
    _x, y = share
    return _mod_pow(g, y, prime)


def verify_share(
    share: tuple[int, int],
    commitment: int,
    *,
    prime: int = PRIME,
    g: int = PRIMITIVE_ROOT,
) -> bool:
    """Return True when ``g^{y} mod p == commitment`` (share is authentic)."""
    return commit_share(share, prime=prime, g=g) == commitment


def recover_key(
    shares: Sequence[tuple[int, int]],
    *,
    prime: int = PRIME,
) -> int:
    """Reconstruct the escrowed key from a quorum of shares (Lagrange at 0)."""
    if len(shares) < 2:
        raise EscrowError("need at least 2 shares to reconstruct the key")
    return _lagrange_interpolate(shares, 0, prime)


# --------------------------------------------------------------------------- #
# Custody chain
# --------------------------------------------------------------------------- #


def custody_chain_hash(prev_hash: str, index: int, from_holder: str, to_holder: str) -> str:
    """Return the SHA-256 chain commitment for a custody transfer."""
    payload = f"{prev_hash}|{index}|{from_holder}|{to_holder}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_custody_transfer(
    index: int,
    from_holder: str,
    to_holder: str,
    prev_hash: str,
) -> CustodyTransfer:
    """Build a custody transfer with its own committed chain hash."""
    chain_hash = custody_chain_hash(prev_hash, index, from_holder, to_holder)
    return CustodyTransfer(
        index=index,
        from_holder=from_holder,
        to_holder=to_holder,
        prev_hash=prev_hash,
        chain_hash=chain_hash,
    )


def custody_chain_for(holders: Sequence[str]) -> tuple[CustodyTransfer, ...]:
    """Build a deterministic SHA-256 hash-chained custody ledger over ``holders``.

    The first transfer is the genesis record (``from_holder == ""``), and every
    subsequent transfer chains to the previous one via its ``chain_hash``, so
    the ledger is append-only: a handoff cannot be inserted, removed, or edited
    without breaking every later link. Returns an empty tuple for an empty
    ``holders`` sequence.
    """
    chain: list[CustodyTransfer] = []
    prev_hash = ""
    for index, holder in enumerate(holders):
        from_holder = "" if index == 0 else holders[index - 1]
        transfer = generate_custody_transfer(index, from_holder, holder, prev_hash)
        chain.append(transfer)
        prev_hash = transfer.chain_hash
    return tuple(chain)


def custody_chain_is_consistent(chain: Sequence[CustodyTransfer]) -> bool:
    """Return whether ``chain`` is a well-formed linked custody ledger.

    Every transfer must be a consecutive index starting at 0, carry a non-empty
    ``chain_hash`` that recomputes from its own ``(prev_hash, index,
    from_holder, to_holder)``, and chain to the record before it. This is the
    derivable property a custody-audit verdict checks.
    """
    prev_hash = ""
    for index, transfer in enumerate(chain):
        if transfer.index != index:
            return False
        if transfer.prev_hash != prev_hash:
            return False
        if transfer.chain_hash != custody_chain_hash(
            transfer.prev_hash, transfer.index, transfer.from_holder, transfer.to_holder
        ):
            return False
        prev_hash = transfer.chain_hash
    return True


# --------------------------------------------------------------------------- #
# High-level escrow
# --------------------------------------------------------------------------- #


def create_escrow(
    key: int,
    *,
    threshold: int,
    num_shares: int,
    custodian_labels: Sequence[str],
    seed: int = 0,
    prime: int = PRIME,
    custody_chain: Sequence[CustodyTransfer] = (),
) -> EscrowState:
    """Create a deterministic escrow for ``key`` under a quorum rule.

    Args:
        key: The ATAC key to escrow.
        threshold: Quorum size required to release the key.
        num_shares: Total shares to distribute among custodians.
        custodian_labels: Named custodians (``num_shares`` of them).
        seed: Fixed RNG seed.
        prime: Field modulus.
        custody_chain: The SHA-256 hash-chained handoff ledger the escrow
            carries (see :func:`custody_chain_for`); empty by default.

    Returns:
        An :class:`EscrowState` binding fingerprint, shares, commitments, and
        the custody chain.
    """
    if len(custodian_labels) != num_shares:
        raise EscrowError(f"need {num_shares} custodian labels, got {len(custodian_labels)}")
    shares = split_key(key, threshold, num_shares, prime=prime, seed=seed)
    commitments = tuple(commit_share(share, prime=prime) for share in shares)
    fingerprint = hashlib.sha256(str(key).encode("utf-8")).hexdigest()
    return EscrowState(
        key_fingerprint=fingerprint,
        threshold=threshold,
        num_shares=num_shares,
        prime=prime,
        shares=shares,
        commitments=commitments,
        custodian_labels=tuple(custodian_labels),
        custody_chain=tuple(custody_chain),
    )


def release_key(
    escrow: EscrowState,
    share_indices: Sequence[int],
    *,
    verify: bool = True,
) -> int:
    """Recover the escrowed key from a quorum of authenticated shares.

    Args:
        escrow: The escrow holding the shares and commitments.
        share_indices: Positions (into ``escrow.shares``) forming the quorum.
        verify: When True (default), every share is checked against its
            commitment first; a failed check raises :class:`EscrowError`.

    Returns:
        The reconstructed key, confirmed to match the escrow fingerprint.
    """
    if len(share_indices) < escrow.threshold:
        raise EscrowError(f"release needs a quorum of {escrow.threshold} shares, got {len(share_indices)}")
    chosen: list[tuple[int, int]] = []
    for idx in share_indices:
        if not (0 <= idx < len(escrow.shares)):
            raise EscrowError(f"share index {idx} out of range")
        share = escrow.shares[idx]
        if verify and not verify_share(share, escrow.commitments[idx], prime=escrow.prime):
            raise EscrowError(f"share {idx} failed verification (tampered in custody)")
        chosen.append(share)
    key = recover_key(chosen, prime=escrow.prime)
    if hashlib.sha256(str(key).encode("utf-8")).hexdigest() != escrow.key_fingerprint:
        raise EscrowError("reconstructed key does not match the escrowed fingerprint")
    return key
