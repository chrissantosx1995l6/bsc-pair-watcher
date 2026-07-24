import argparse
import logging
import sys
from bsc_watcher.config import Config


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args(argv=None) -> Config:
    cfg = Config.from_env()
    parser = argparse.ArgumentParser(description="Watch BSC factory pair deployments and sync logs.")
    parser.add_argument("--rpc", dest="rpc_url", default=cfg.rpc_url, help="JSON-RPC endpoint url")
    parser.add_argument("--db", dest="db_path", default=cfg.db_path, help="Path to SQLite database file")
    parser.add_argument("--chunk-size", dest="block_chunk_sz", type=int, default=cfg.block_chunk_sz, help="Blocks per getLogs request")
    parser.add_argument("--interval", dest="poll_interval", type=float, default=cfg.poll_interval, help="Polling loop sleep in seconds")
    parser.add_argument("--start-block", dest="start_block", type=int, default=cfg.start_block, help="Explicit block to start from (0 = latest db block)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    cfg.rpc_url = args.rpc_url
    cfg.db_path = args.db_path
    cfg.block_chunk_sz = args.block_chunk_sz
    cfg.poll_interval = args.poll_interval
    cfg.start_block = args.start_block
    return cfg


def main(argv=None) -> int:
    cfg = parse_args(argv)
    # watcher import deferred so cli --help is instant
    from bsc_watcher.watcher import Watcher
    
    watcher = Watcher(cfg)
    try:
        watcher.run()
    except KeyboardInterrupt:
        logging.info("stopped by user")
    return 0
