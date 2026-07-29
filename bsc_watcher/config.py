import os
from dataclasses import dataclass, field
from typing import List


DEFAULT_RPC_URL = "https://bsc-dataseed.binance.org/"
PANCAKE_V2_FACTORY = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"
PANCAKE_V3_FACTORY = "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865"
WBNB_ADDRESS = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
BUSD_ADDRESS = "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"
USDT_ADDRESS = "0x55d398326f99059fF775485246999027B3197955"


@dataclass
class Config:
    """Runtime configuration passed around the pipeline."""
    rpc_url: str = DEFAULT_RPC_URL
    factories: List[str] = field(default_factory=lambda: [PANCAKE_V2_FACTORY, PANCAKE_V3_FACTORY])
    db_path: str = "bsc_watcher.db"
    poll_interval: float = 2.0
    block_chunk_sz: int = 50
    start_block: int = 0
    min_reserve_usd: float = 0.0
    telegram_token: str = ""
    telegram_chat_id: str = ""
    silent: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        factories_raw = os.getenv("BSC_FACTORIES", f"{PANCAKE_V2_FACTORY},{PANCAKE_V3_FACTORY}")
        factories = [f.strip() for f in factories_raw.split(",") if f.strip()]

        return cls(
            rpc_url=os.getenv("BSC_RPC_URL", DEFAULT_RPC_URL),
            factories=factories,
            db_path=os.getenv("BSC_DB_PATH", "bsc_watcher.db"),
            poll_interval=float(os.getenv("BSC_POLL_INTERVAL", "2.0")),
            block_chunk_sz=int(os.getenv("BSC_CHUNK_SIZE", "50")),
            start_block=int(os.getenv("BSC_START_BLOCK", "0")),
            min_reserve_usd=float(os.getenv("BSC_MIN_RESERVE_USD", "0")),
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            silent=os.getenv("BSC_SILENT", "").lower() in ("1", "true", "yes"),
        )
