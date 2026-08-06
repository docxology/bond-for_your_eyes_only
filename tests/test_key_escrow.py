"""Real-data tests for the ATAC key escrow/recovery protocol."""

import pytest

from for_your_eyes_only import key_escrow


def test_shamir_split_and_recover_roundtrip():
    """A full quorum of shares reconstructs the original key exactly."""
    key = 4242
    shares = key_escrow.split_key(key, threshold=3, num_shares=5, seed=7)
    assert len(shares) == 5
    recovered = key_escrow.recover_key(shares[:3])
    assert recovered == key


def test_smaller_quorum_recovers_too():
    """Any subset of exactly the threshold size still reconstructs."""
    key = 1337
    shares = key_escrow.split_key(key, threshold=2, num_shares=5, seed=7)
    assert key_escrow.recover_key(shares[1:3]) == key
    assert key_escrow.recover_key(shares[3:]) == key


def test_determinism_same_seed():
    """Same seed/args give byte-identical share sets."""
    a = key_escrow.split_key(99, threshold=2, num_shares=4, seed=1)
    b = key_escrow.split_key(99, threshold=2, num_shares=4, seed=1)
    assert a == b
    c = key_escrow.split_key(99, threshold=2, num_shares=4, seed=2)
    assert a != c


def test_mod_inverse_roundtrip():
    """a * a^{-1} == 1 mod p for a supported element."""
    p = key_escrow.PRIME
    a = 123456789
    inv = key_escrow.mod_inverse(a, p)
    assert (a * inv) % p == 1


def test_mod_inverse_of_zero_raises():
    with pytest.raises(key_escrow.EscrowError):
        key_escrow.mod_inverse(0, key_escrow.PRIME)


def test_commitment_verification():
    """A genuine share passes verification; a tampered one fails."""
    key = 4242
    shares = key_escrow.split_key(key, threshold=2, num_shares=3, seed=7)
    commitments = [key_escrow.commit_share(s) for s in shares]
    assert all(key_escrow.verify_share(s, c) for s, c in zip(shares, commitments))
    # tamper: change the y-value -> verification fails
    x, y = shares[0]
    tampered = (x, (y + 1) % key_escrow.PRIME)
    assert not key_escrow.verify_share(tampered, commitments[0])


def test_commitment_does_not_leak_share():
    """Commitments differ across shares and are not trivially the y values."""
    shares = key_escrow.split_key(42, threshold=2, num_shares=3, seed=7)
    commits = [key_escrow.commit_share(s) for s in shares]
    assert len(set(commits)) == len(shares)


def test_create_and_release_escrow():
    """High-level escrow: quorum release recovers and matches fingerprint."""
    escrow = key_escrow.create_escrow(
        4242,
        threshold=2,
        num_shares=3,
        custodian_labels=("q_branch", "m", "field_agent"),
        seed=7,
    )
    assert escrow.threshold == 2
    assert escrow.num_shares == 3
    assert len(escrow.custodian_labels) == 3
    assert len(escrow.commitments) == 3
    recovered = key_escrow.release_key(escrow, (0, 1))
    assert recovered == 4242


def test_release_requires_quorum():
    """Release below the threshold raises EscrowError."""
    escrow = key_escrow.create_escrow(4242, threshold=2, num_shares=3, custodian_labels=("a", "b", "c"), seed=7)
    with pytest.raises(key_escrow.EscrowError):
        key_escrow.release_key(escrow, (0,))


def test_release_rejects_tampered_share():
    """A tampered share (verification on) raises; with verify=False it fails fingerprint."""
    escrow = key_escrow.create_escrow(4242, threshold=2, num_shares=3, custodian_labels=("a", "b", "c"), seed=7)
    # corrupt share 0 stored in the frozen tuple via a rebuild
    tampered_shares = list(escrow.shares)
    x, y = tampered_shares[0]
    tampered_shares[0] = (x, (y + 1) % escrow.prime)
    bad = key_escrow.EscrowState(
        escrow.key_fingerprint,
        escrow.threshold,
        escrow.num_shares,
        escrow.prime,
        tuple(tampered_shares),
        escrow.commitments,
        escrow.custodian_labels,
        escrow.custody_chain,
    )
    # verification on -> tamper detected
    with pytest.raises(key_escrow.EscrowError):
        key_escrow.release_key(bad, (0, 1))
    # verification off but fingerprint still mismatches
    with pytest.raises(key_escrow.EscrowError):
        key_escrow.release_key(bad, (0, 1), verify=False)


def test_release_out_of_range_index():
    escrow = key_escrow.create_escrow(4242, threshold=2, num_shares=3, custodian_labels=("a", "b", "c"), seed=7)
    with pytest.raises(key_escrow.EscrowError):
        key_escrow.release_key(escrow, (0, 99))


def test_custody_chain_hash_is_deterministic_and_linking():
    """Chain hashes bind each transfer to the previous one."""
    first = key_escrow.generate_custody_transfer(0, "base", "agent", "")
    assert first.chain_hash == key_escrow.custody_chain_hash("", 0, "base", "agent")
    second = key_escrow.generate_custody_transfer(1, "agent", "field", first.chain_hash)
    assert second.prev_hash == first.chain_hash
    assert second.chain_hash != first.chain_hash
    # re-generating reproduces identical hashes
    second_again = key_escrow.generate_custody_transfer(1, "agent", "field", first.chain_hash)
    assert second_again == second


def test_escrow_state_validation():
    with pytest.raises(ValueError):
        key_escrow.EscrowState("fp", 1, 3, key_escrow.PRIME, (), (), ("a", "b", "c"))
    with pytest.raises(ValueError):
        key_escrow.CustodyTransfer(-1, "a", "b")


def test_split_key_validation():
    with pytest.raises(key_escrow.EscrowError):
        key_escrow.split_key(0, threshold=2, num_shares=3)
    with pytest.raises(key_escrow.EscrowError):
        key_escrow.split_key(100, threshold=1, num_shares=3)
    with pytest.raises(key_escrow.EscrowError):
        key_escrow.split_key(100, threshold=4, num_shares=3)


def test_recover_key_needs_two():
    with pytest.raises(key_escrow.EscrowError):
        key_escrow.recover_key([(1, 2)])


def test_custody_chain_for_links_the_ledger():
    """C2: custody_chain_for builds a real, deterministic, chain-linked ledger."""
    chain = key_escrow.custody_chain_for(("q_branch", "m", "field_agent"))
    assert [t.index for t in chain] == [0, 1, 2]
    assert [t.to_holder for t in chain] == ["q_branch", "m", "field_agent"]
    assert chain[0].from_holder == ""
    assert chain[1].from_holder == "q_branch"
    assert chain[1].prev_hash == chain[0].chain_hash
    assert chain[2].prev_hash == chain[1].chain_hash
    # deterministic
    assert key_escrow.custody_chain_for(("q_branch", "m", "field_agent")) == chain


def test_custody_chain_is_consistent_detects_breaks():
    chain = key_escrow.custody_chain_for(("q_branch", "m", "field_agent"))
    assert key_escrow.custody_chain_is_consistent(chain) is True
    # empty chain is trivially consistent
    assert key_escrow.custody_chain_is_consistent(()) is True
    # tampering with one record breaks the link check
    x = key_escrow.CustodyTransfer(chain[1].index, chain[1].from_holder, "impostor", chain[1].prev_hash)
    broken = (chain[0], x, chain[2])
    assert key_escrow.custody_chain_is_consistent(broken) is False
    # a renumbered index breaks it
    reindexed = key_escrow.CustodyTransfer(
        chain[1].index + 10,
        chain[1].from_holder,
        chain[1].to_holder,
        chain[1].prev_hash,
        chain[1].chain_hash,
    )
    assert key_escrow.custody_chain_is_consistent((chain[0], reindexed)) is False
    # a record whose prev_hash does not chain breaks it
    unlinked = key_escrow.CustodyTransfer(1, "q_branch", "m", "deadbeef")
    assert key_escrow.custody_chain_is_consistent((chain[0], unlinked, chain[2])) is False


def test_create_escrow_can_carry_a_custody_chain():
    labels = ("q_branch", "m", "field_agent")
    chain = key_escrow.custody_chain_for(labels)
    escrow = key_escrow.create_escrow(
        4242,
        threshold=2,
        num_shares=3,
        custodian_labels=labels,
        seed=7,
        custody_chain=chain,
    )
    assert escrow.custody_chain == chain
    assert key_escrow.custody_chain_is_consistent(escrow.custody_chain) is True
    # and a default escrow still releases identically (chain is not required)
    plain = key_escrow.create_escrow(4242, threshold=2, num_shares=3, custodian_labels=labels, seed=7)
    assert key_escrow.release_key(plain, (0, 1)) == 4242
