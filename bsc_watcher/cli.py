import argparse
import logging
import sys
from bsc_watcher.config import Config


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # httpx and urllib3 spam get noisy on debug
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def parse_args(argv=None) -> tuple[Config, bool]:
    cfg = Config.from_env()
    parser = argparse.ArgumentParser(
        prog="bsc-watcher",
        description="Personal daemon watching BSC factory pairs and liquidity injections."
    )
    parser.add_argument("--rpc", dest="rpc_url", default=cfg.rpc_url, help="JSON-RPC endpoint url")
    parser.add_argument("--db", dest="db_path", default=cfg.db_path, help="Path to SQLite database file")
    parser.add_argument("--chunk-size", dest="block_chunk_sz", type=int, default=cfg.block_chunk_sz, help="Blocks per eth_getLogs call")
    parser.add_argument("--interval", dest="poll_interval", type=float, default=cfg.poll_interval, help="Polling loop sleep in seconds")
    parser.add_argument("--start-block", dest="start_block", type=int, default=cfg.start_block, help="Explicit starting block")
    parser.add_argument("--min-reserve", dest="min_reserve_usd", type=float, default=cfg.min_reserve_usd, help="Min USD reserve to alert")
    parser.add_argument("--tg-token", dest="telegram_token", default=cfg.telegram_token, help="Telegram bot token for alerts")
    parser.add_argument("--tg-chat", dest="telegram_chat_id", default=cfg.telegram_chat_id, help="Telegram chat ID")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and parse but do not persist or notify")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only errors and warnings")

    args = parser.parse_args(argv)
    setup_logging(args.verbose, args.quiet)

    cfg.rpc_url = args.rpc_url
    cfg.db_path = args.db_path
    cfg.block_chunk_sz = args.block_chunk_sz
    cfg.poll_interval = args.poll_interval
    cfg.start_block = args.start_block
    cfg.min_reserve_usd = args.min_reserve_usd
    cfg.telegram_token = args.telegram_token
    cfg.telegram_chat_id = args.telegram_chat_id
    return cfg, args.dry_run


def main(argv=None) -> int:
    cfg, dry_run = parse_args(argv)
    from bsc_watcher.watcher import Watcher

    watcher = Watcher(cfg, dry_run=dry_run)
    try:
        watcher.run()
    except KeyboardInterrupt:
        logging.getLogger("bsc_watcher").info("interrupted, shutting down clean")
    except Exception as exc:
        logging.getLogger("bsc_watcher").exception("fatal runtime crash: %s", exc)
        return 1
    return 0
