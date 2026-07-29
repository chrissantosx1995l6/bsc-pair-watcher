"""PancakeSwap pair and liquidity watcher for BSC."""

from bsc_watcher.config import WatcherConfig
from bsc_watcher.watcher import Watcher

__version__ = "0.2.1"
__all__ = ["Watcher", "WatcherConfig", "__version__"]
