from typing import Optional, Union
from bsc_watcher.events import MintEvent, PairCreatedEvent, RawLog, SyncEvent

# keccak256("PairCreated(address,address,address,uint256)")
TOPIC_PAIR_CREATED = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"

# keccak256("Mint(address,uint256,uint256)")
TOPIC_MINT = "0x4c209b02800435e65597402b2d1359e5288b33d87d589e3a7a535d2f4ec73a37"

# keccak256("Sync(uint112,uint112)")
TOPIC_SYNC = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"


def _clean_hex(hex_str: str) -> str:
    return hex_str[2:] if hex_str.startswith("0x") else hex_str


def _topic_to_address(topic: str) -> str:
    clean = _clean_hex(topic)
    # 32-byte word: address takes last 20 bytes (40 hex chars)
    return "0x" + clean[-40:].lower()


def decode_pair_created(log: RawLog) -> Optional[PairCreatedEvent]:
    """Decodes UniswapV2/PancakeSwap PairCreated event without web3 dependencies."""
    if not log.topics or log.topics[0] != TOPIC_PAIR_CREATED:
        return None
    if len(log.topics) < 3:
        return None

    token0 = _topic_to_address(log.topics[1])
    token1 = _topic_to_address(log.topics[2])

    # data has non-indexed fields: pair address (32 bytes) + uint256 allPairs length (32 bytes)
    data = _clean_hex(log.data)
    if len(data) < 128:
        return None

    # print(f"debug pair data: {data[:128]}")
    pair_raw = data[:64]
    pair = "0x" + pair_raw[-40:].lower()
    pair_index = int(data[64:128], 16)

    return PairCreatedEvent(
        token0=token0,
        token1=token1,
        pair=pair,
        pair_index=pair_index,
        factory=log.address,
        block_number=log.block_number,
        tx_hash=log.tx_hash,
        log_index=log.log_index,
    )


def decode_mint(log: RawLog) -> Optional[MintEvent]:
    if not log.topics or log.topics[0] != TOPIC_MINT:
        return None
    if len(log.topics) < 2:
        return None

    sender = _topic_to_address(log.topics[1])
    data = _clean_hex(log.data)
    if len(data) < 128:
        return None

    amount0 = int(data[:64], 16)
    amount1 = int(data[64:128], 16)

    return MintEvent(
        pair=log.address,
        sender=sender,
        amount0=amount0,
        amount1=amount1,
        block_number=log.block_number,
        tx_hash=log.tx_hash,
        log_index=log.log_index,
    )


def decode_sync(log: RawLog) -> Optional[SyncEvent]:
    if not log.topics or log.topics[0] != TOPIC_SYNC:
        return None

    data = _clean_hex(log.data)
    # uint112 reserve0, uint112 reserve1 padded to 32 bytes each
    if len(data) < 128:
        return None

    # FIXME: check if we need to guard against overflow on corrupted non-standard sync events
    r0 = int(data[:64], 16)
    r1 = int(data[64:128], 16)

    return SyncEvent(
        pair=log.address,
        reserve0=r0,
        reserve1=r1,
        block_number=log.block_number,
        tx_hash=log.tx_hash,
        log_index=log.log_index,
    )


def decode_any_dex_event(log: RawLog) -> Optional[Union[PairCreatedEvent, MintEvent, SyncEvent]]:
    if not log.topics:
        return None
    top = log.topics[0]
    if top == TOPIC_PAIR_CREATED:
        return decode_pair_created(log)
    if top == TOPIC_MINT:
        return decode_mint(log)
    if top == TOPIC_SYNC:
        return decode_sync(log)
    return None
