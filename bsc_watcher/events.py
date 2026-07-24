from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class RawLog:
    address: str
    topics: List[str]
    data: str
    block_number: int
    tx_hash: str
    log_index: int
    removed: bool = False

    @classmethod
    def from_rpc(cls, item: Dict[str, Any]) -> "RawLog":
        block_num = item.get("blockNumber", "0x0")
        log_idx = item.get("logIndex", "0x0")
        
        return cls(
            address=item["address"].lower(),
            topics=[t.lower() for t in item.get("topics", [])],
            data=item.get("data", "0x"),
            block_number=int(block_num, 16) if isinstance(block_num, str) else block_num,
            tx_hash=item.get("transactionHash", ""),
            log_index=int(log_idx, 16) if isinstance(log_idx, str) else log_idx,
            removed=bool(item.get("removed", False)),
        )


@dataclass
class PairCreatedEvent:
    token0: str
    token1: str
    pair: str
    pair_index: int
    factory: str
    block_number: int
    tx_hash: str
    log_index: int


@dataclass
class MintEvent:
    pair: str
    sender: str
    amount0: int
    amount1: int
    block_number: int
    tx_hash: str
    log_index: int
