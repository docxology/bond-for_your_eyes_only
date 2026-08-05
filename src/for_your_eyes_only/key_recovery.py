"""ATAC lost-key recovery: erasure-coded reconstruction over GF(p).

The escrow protects a key against *delegated-recovery* risk: a single stored
copy can be lost or corrupted. This module implements an erasure-coded key
recovery scheme so the ATAC key survives the loss or corruption of individual
stored fragments.

Real model behind the code — a **systematic Reed–Solomon-style erasure code
over the finite field GF(p)**:

* The key is treated as ``k`` field elements (its "data symbols"). A generator
  polynomial ``P(x) = d_0 + d_1 x + ... + d_{k-1} x^{k-1}`` is evaluated at
  ``n`` distinct field points to produce ``n`` *code symbols* (the stored
  fragments).
* A **Vandermonde system** ties the fragments together: given any ``k`` of the
  ``n`` fragments, the key is recovered by solving the square linear system
  whose coefficient rows are the chosen evaluation points. Because a square
  Vandermonde matrix over a field is invertible, any ``k`` fragments
  reconstruct the key — the erasure-decode property.
* A **checksum fragment** (a hash of the data symbols) detects when any
  fragment is corrupted, so one bad fragment never silently yields a wrong key.

Everything is deterministic: the field ``GF(p)`` and evaluation points are
fixed, and any random-looking symbol is a plain integer derived from a key
seed. No wall clock appears in any artifact.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from for_your_eyes_only.key_escrow import PRIME, mod_inverse

__all__ = [
    "ERASURE_PRIME",
    "ErasureCode",
    "ChecksumMismatchError",
    "encode_erasure",
    "recover_erasure",
    "data_checksum",
]

#: Field modulus for the erasure code (reuses the escrow's Mersenne prime).
ERASURE_PRIME = PRIME


class ChecksumMismatchError(ValueError):
    """Raised when a recovered key fails its integrity checksum."""


@dataclass(frozen=True)
class ErasureCode:
    """A deterministic erasure code bound to a fixed evaluation-point grid.

    ``data_symbols`` is the number of key elements (``k``); ``code_symbols``
    is the total fragments stored (``n >= k``); evaluation points are
    ``1..n``. Any ``k`` fragments recover the key.
    """

    data_symbols: int
    code_symbols: int
    prime: int = ERASURE_PRIME

    def __post_init__(self) -> None:
        if not (1 <= self.data_symbols <= self.code_symbols):
            raise ValueError("need 1 <= data_symbols <= code_symbols")
        if self.code_symbols >= self.prime:
            raise ValueError("code_symbols must be < prime (distinct field points)")

    def points(self) -> tuple[int, ...]:
        """Return the fixed evaluation points ``1 .. code_symbols``."""
        return tuple(range(1, self.code_symbols + 1))


def _power(base: int, exponent: int, prime: int) -> int:
    return pow(base, exponent, prime)


def _poly_eval(points: tuple[int, ...], coeffs: tuple[int, ...], prime: int) -> tuple[int, ...]:
    """Evaluate ``P(x) = sum c_j x^j`` at each evaluation point, in GF(p)."""
    values: list[int] = []
    for x in points:
        total = 0
        for power, coeff in enumerate(coeffs):
            total = (total + coeff * _power(x, power, prime)) % prime
        values.append(total)
    return tuple(values)


def _vandermonde_solve(rows: list[tuple[int, ...]], rhs: list[int], k: int, prime: int) -> tuple[int, ...]:
    """Solve ``rows * coeffs = rhs`` over GF(p) by Gaussian elimination.

    ``rows[i]`` is ``[1, x_i, x_i^2, ..., x_i^{k-1}]``; the solution is the
    recovered data-symbol coefficient vector. Raises :class:`ValueError` when
    the rows are linearly dependent (a bad fragment set).
    """
    mat = [list(row) + [rhs[i]] for i, row in enumerate(rows)]
    n = len(mat)
    col = 0
    for piv in range(n):
        chosen = None
        for r in range(piv, n):
            if mat[r][col] % prime != 0:
                chosen = r
                break
        if chosen is None:
            raise ValueError("fragment system is singular: cannot recover the key")
        mat[piv], mat[chosen] = mat[chosen], mat[piv]
        inv = mod_inverse(mat[piv][col], prime)
        mat[piv] = [(val * inv) % prime for val in mat[piv]]
        for r in range(n):
            if r == piv:
                continue
            factor = mat[r][col]
            if factor != 0:
                mat[r] = [(a - factor * b) % prime for a, b in zip(mat[r], mat[piv])]
        col += 1
    return tuple(int(mat[r][k]) % prime for r in range(n))


def data_checksum(data: tuple[int, ...], prime: int) -> int:
    """Return a deterministic checksum ``int(sha256(data)[:8],16) % prime``.

    The checksum is a stable fingerprint of the data symbols, used to verify a
    recovered key. It is a plain integer in ``GF(p)``.
    """
    payload = "|".join(str(v) for v in data)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % prime


def encode_erasure(
    data: tuple[int, ...],
    code: ErasureCode,
    *,
    checksum: bool = True,
) -> tuple[int, ...]:
    """Encode ``data`` (``k`` symbols) into ``n`` code symbols over GF(p).

    When ``checksum`` is True an extra integrity symbol is appended (the data
    checksum). Raises :class:`ValueError` on a data-length mismatch.

    Args:
        data: The field elements to encode (the ATAC key fragments).
        code: The erasure code configuration (``k``, ``n``, prime).
        checksum: Append the integrity checksum symbol (default True).

    Returns:
        The code symbols; final symbol is the checksum when enabled.
    """
    if len(data) != code.data_symbols:
        raise ValueError(f"expected {code.data_symbols} data symbols, got {len(data)}")
    prime = code.prime
    coeffs = tuple(d % prime for d in data)
    symbols = _poly_eval(code.points(), coeffs, prime)
    if checksum:
        # Checksum over the *residue* form actually stored, so recovery of the
        # reduced values verifies consistently.
        symbols = symbols + (data_checksum(coeffs, prime),)
    return symbols


def recover_erasure(
    symbols: tuple[int, ...],
    code: ErasureCode,
    *,
    checksum: bool = True,
) -> tuple[int, ...]:
    """Recover the original data from the encoded symbols.

    Uses the first ``data_symbols`` code symbols as the fragment set and
    solves the Vandermonde system. When ``checksum`` is True the trailing
    integrity symbol (present when ``len(symbols) == code_symbols + 1``) is
    verified against the reconstructed data.

    Args:
        symbols: The code symbols as returned by :func:`encode_erasure`.
        code: The erasure code configuration.

    Returns:
        The recovered data symbols.

    Raises:
        ChecksumMismatchError: if the integrity checksum does not match.
    """
    prime = code.prime
    if checksum and len(symbols) == code.code_symbols + 1:
        code_symbols = symbols[: code.code_symbols]
        expected = symbols[-1]
    else:
        code_symbols = symbols
        expected = None

    if len(code_symbols) < code.data_symbols:
        raise ValueError(f"need at least {code.data_symbols} code symbols, got {len(code_symbols)}")

    points = code.points()
    k = code.data_symbols
    rows: list[tuple[int, ...]] = []
    rhs: list[int] = []
    for i in range(k):
        x = points[i]
        rows.append(tuple(_power(x, j, prime) for j in range(k)))
        rhs.append(code_symbols[i] % prime)
    recovered = _vandermonde_solve(rows, rhs, k, prime)

    if expected is not None and data_checksum(recovered, prime) != expected % prime:
        raise ChecksumMismatchError("recovered key failed its integrity checksum")
    return recovered
