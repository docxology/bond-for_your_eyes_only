"""Real-data tests for the ATAC erasure-coded key recovery module."""

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
    """Erasure property: any k of the n code symbols reconstruct the key."""
    code = kr.ErasureCode(data_symbols=3, code_symbols=5)
    data = (10, 20, 30)
    encoded = kr.encode_erasure(data, code, checksum=False)
    assert len(encoded) == 5
    # use only the first 3 (data-carrying portion) -> still recovers
    recovered = kr.recover_erasure(encoded[:3], code, checksum=False)
    assert recovered == data


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
    with pytest.raises(ValueError):
        kr.encode_erasure((1, 2), kr.ErasureCode(3, 5))
    with pytest.raises(ValueError):
        kr.recover_erasure((1, 2), kr.ErasureCode(4, 6))


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
