# bsc-watcher

Personal daemon that polls BSC JSON-RPC for PancakeSwap v2 factory `PairCreated` events and pair `Mint` (liquidity injection) logs. Saves state to a local SQLite database and pushes alerts to terminal output or Telegram.

Doesn't rely on web3.py or heavy websocket stacks. Just raw `eth_getLogs` batches and custom topic decoders.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Copy `.env.example` to `.env` if you want telegram alerts:

```bash
BSC_RPC_URL=https://bsc-dataseed.binance.org
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=-1001234567890
MIN_LIQUIDITY_BNB=0.5
```

## Running

Run the daemon with default BSC public node:

```bash
bsc-watch
```

Or pass options directly:

```bash
bsc-watch --rpc https://rpc.ankr.com/bsc --db ./data/pairs.db --interval 1.5 --min-bnb 1.0
```

Backfill recent blocks on startup:

```bash
bsc-watch --backfill 500
```

## SQLite inspection

Pairs and liquidity additions are stored in `pairs.db` (or whatever path passed via `--db`):

```bash
sqlite3 pairs.db "SELECT pair_address, token0_symbol, token1_symbol, initial_bnb, created_at FROM pairs ORDER BY id DESC LIMIT 10;"
```

<!-- checked: 2026-09-08 -->
