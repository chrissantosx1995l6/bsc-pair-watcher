from bsc_watcher.abi import (
    decode_pair_created,
    decode_mint,
    hex_to_address,
    hex_to_uint256,
)


def test_hex_to_address():
    padded = "0x000000000000000000000000bb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
    addr = hex_to_address(padded)
    assert addr == "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"


def test_hex_to_uint256():
    raw = "0x0000000000000000000000000000000000000000000000056bc75e2d63100000"
    val = hex_to_uint256(raw)
    assert val == 100000000000000000000


