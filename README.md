# bsc-watcher

Simple poller for PancakeSwap v2 PairCreated events over raw BSC JSON-RPC.
I wrote this to catch new pools straight from the node before DexScreener/GeckoTerminal show them.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick start

```bash
bsc-watch --rpc https://bsc-dataseed1.binance.org
```
