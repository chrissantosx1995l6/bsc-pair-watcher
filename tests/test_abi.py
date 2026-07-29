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


def test_decode_pair_created_success():
    fake_log = {
        "topics": [
            "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9",
            "0x000000000000000000000000bb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c",
            "0x00000000000000000000000055d398326f99059ff775485246999027b3197955",
        ],
        # address + uint pair length in data
        "data": "0x00000000000000000000000058f876857a02d6762e0101bb5c46a8c1ed44dc160000000000000000000000000000000000000000000000000000000000000001",
        "blockNumber": "0x1c8b320",
        "transactionHash": "0xabc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abc",
    }
    evt = decode_pair_created(fake_log)
    assert evt is not None
    assert evt.token0 == "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
    assert evt.token1 == "0x55d398326f99059ff775485246999027b3197955"
    assert evt.pair_address == "0x58f876857a02d6762e0101bb5c46a8c1ed44dc16"
    assert evt.block_number == 29930272


def test_decode_pair_created_invalid_topic():
    fake_log = {
        "topics": ["0xdeadbeef"],
        "data": "0x",
        "blockNumber": "0x1",
        "transactionHash": "0x1",
    }
    assert decode_pair_created(fake_log) is None
