"""Real-data tests for the ATAC erasure-coded key recovery module."""

import itertools

import pytest

from for_your_eyes_only import key_recovery as kr
from for_your_eyes_only.key_escrow import PRIME


def test_encode_recover_roundtrip():
    code = kr.ErasureCode(data_symbols=4, code_symbols=6)
    data = (1, 2, 3, 4)
    encoded = kr.encode_erasure(data, code)
    assert len(encoded) == 7  # 6 code symbols + 1 checksum
    recovered = kr.recover_erasure(encoded, code)
    assert recovered == data


def test_any_k_fragments_recover():
    """Erasure property: *any* k of the n code symbols reconstruct the key.

    The leading-k case is the easy one and proves nothing about erasure — it is
    what a decoder that ignored fragment positions would also pass. Every
    non-leading combination must work too.
    """
    code = kr.ErasureCode(data_symbols=3, code_symbols=5)
    data = (10, 20, 30)
    encoded = kr.encode_erasure(data, code, checksum=False)
    assert len(encoded) == 5

    combos = list(itertools.combinations(range(5), 3))
    assert len(combos) == 10
    for survivors in combos:
        recovered = kr.recover_erasure(encoded, code, checksum=False, indices=survivors)
        assert recovered == data, f"fragments {survivors} failed to recover the key"

    # Explicitly include a set containing none of the leading fragments.
    assert kr.recover_erasure(encoded, code, checksum=False, indices=(2, 3, 4)) == data


def test_any_k_fragments_recover_with_checksum():
    """The erasure property survives the checksum-carrying encoding too."""
    code = kr.ErasureCode(data_symbols=4, code_symbols=6)
    data = (11, 22, 33, 44)
    encoded = kr.encode_erasure(data, code)
    assert len(encoded) == 7
    # Fragments 0 and 1 are "lost": decode from the trailing four.
    assert kr.recover_erasure(encoded, code, indices=(2, 3, 4, 5)) == data


def test_recover_rejects_bad_index_sets():
    code = kr.ErasureCode(data_symbols=3, code_symbols=5)
    encoded = kr.encode_erasure((1, 2, 3), code, checksum=False)
    with pytest.raises(ValueError, match="exactly 3"):
        kr.recover_erasure(encoded, code, checksum=False, indices=(0, 1))
    with pytest.raises(ValueError, match="distinct"):
        kr.recover_erasure(encoded, code, checksum=False, indices=(0, 1, 1))
    with pytest.raises(ValueError, match="out of range"):
        kr.recover_erasure(encoded, code, checksum=False, indices=(0, 1, 99))


def test_requested_checksum_without_checksum_symbol_is_an_error():
    """Asking to be protected when there is nothing to check must not pass silently."""
    code = kr.ErasureCode(data_symbols=4, code_symbols=6)
    encoded = kr.encode_erasure((1, 2, 3, 4), code, checksum=False)
    assert len(encoded) == 6
    with pytest.raises(ValueError, match="no checksum symbol present"):
        kr.recover_erasure(encoded, code, checksum=True)


def test_deterministic_encoding():
    code = kr.ErasureCode(data_symbols=4, code_symbols=6)
    a = kr.encode_erasure((1, 2, 3, 4), code)
    b = kr.encode_erasure((1, 2, 3, 4), code)
    assert a == b


def test_different_data_different_code():
    code = kr.ErasureCode(data_symbols=4, code_symbols=6)
    a = kr.encode_erasure((1, 2, 3, 4), code)
    b = kr.encode_erasure((5, 6, 7, 8), code)
    assert a != b


def test_checksum_detects_corruption():
    code = kr.ErasureCode(data_symbols=4, code_symbols=6)
    data = (1, 2, 3, 4)
    encoded = kr.encode_erasure(data, code)
    # corrupt one code symbol (not the checksum)
    corrupted = encoded[:3] + ((encoded[3] + 1) % PRIME,) + encoded[4:]
    with pytest.raises(kr.ChecksumMismatchError):
        kr.recover_erasure(corrupted, code)


def test_no_checksum_mode_recover():
    code = kr.ErasureCode(data_symbols=4, code_symbols=6)
    encoded = kr.encode_erasure((9, 9, 9, 9), code, checksum=False)
    assert len(encoded) == 6
    recovered = kr.recover_erasure(encoded, code, checksum=False)
    assert recovered == (9, 9, 9, 9)


def test_validation():
    with pytest.raises(ValueError):
        kr.ErasureCode(data_symbols=0, code_symbols=2)
    with pytest.raises(ValueError):
        kr.ErasureCode(data_symbols=5, code_symbols=2)  # k > n
    with pytest.raises(ValueError):
        kr.ErasureCode(data_symbols=2, code_symbols=PRIME)  # n >= p
    with pytest.raises(ValueError, match="expected 3 data symbols"):
        kr.encode_erasure((1, 2), kr.ErasureCode(3, 5))
    with pytest.raises(ValueError, match="need at least 4 code symbols"):
        kr.recover_erasure((1, 2), kr.ErasureCode(4, 6), checksum=False)


def test_fields_in_field():
    code = kr.ErasureCode(data_symbols=3, code_symbols=5)
    encoded = kr.encode_erasure((PRIME + 1, PRIME + 2, PRIME + 3), code)
    # symbols are reduced mod p
    assert all(0 <= s < PRIME for s in encoded)
    # recover still returns reduced values in (0, p)
    recovered = kr.recover_erasure(encoded, code)
    assert all(0 <= v < PRIME for v in recovered)


def test_canonical_mission_recovery_matches():
    """The mission's canonical recovery reconstructs its key data symbols."""
    from for_your_eyes_only.mission import canonical_mission

    sc = canonical_mission()
    assert list(sc.recovery_recovered) == list(sc.recovery_data)


def test_data_checksum_stable():
    assert kr.data_checksum((1, 2, 3), PRIME) == kr.data_checksum((1, 2, 3), PRIME)
    assert kr.data_checksum((1, 2, 3), PRIME) != kr.data_checksum((1, 2, 4), PRIME)
