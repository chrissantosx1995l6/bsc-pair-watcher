import time
import logging
from typing import Optional
from bsc_watcher.rpc import JsonRpcClient, RpcError
from bsc_watcher.storage import Storage
from bsc_watcher.notifier import Notifier
from bsc_watcher.filters import build_pair_created_filter, build_mint_filter
from bsc_watcher.abi import decode_pair_created, decode_mint

log = logging.getLogger("bsc_watcher.watcher")


class Watcher:
    """Polls BSC blocks for new PancakeSwap pairs and mint log spikes."""

    def __init__(
        self,
        rpc: JsonRpcClient,
        storage: Storage,
        notifier: Notifier,
        factory_address: str,
        start_block: Optional[int] = None,
        poll_interval: float = 2.0,
        max_chunk: int = 1000,
        track_mints: bool = True,
    ):
        self.rpc = rpc
        self.storage = storage
        self.notifier = notifier
        self.factory_address = factory_address.lower()
        self.poll_interval = poll_interval
        self.max_chunk = max_chunk
        self.current_chunk = max_chunk
        self.track_mints = track_mints
        self._running = False

        saved_block = self.storage.get_last_block()
        if start_block is not None:
            self.current_block = start_block
        elif saved_block > 0:
            # Rewind 2 blocks just in case of slight BSC tip reorg
            self.current_block = max(0, saved_block - 2)
        else:
            self.current_block = self.rpc.get_block_number()

    def run(self):
        self._running = True
        log.info("watching factory %s from block %d (chunk size: %d)", self.factory_address, self.current_block, self.current_chunk)

        while self._running:
            try:
                latest = self.rpc.get_block_number()
                if latest < self.current_block:
                    time.sleep(self.poll_interval)
                    continue

                to_block = min(latest, self.current_block + self.current_chunk - 1)
                success = self._process_window(self.current_block, to_block)
                if success:
                    self.current_block = to_block + 1
                    self.storage.set_last_block(to_block)
                    # Slowly restore chunk size if we had backed off
                    if self.current_chunk < self.max_chunk:
                        self.current_chunk = min(self.max_chunk, self.current_chunk + 100)

                    if to_block >= latest:
                        time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                log.info("caught interrupt, shutting down")
                break
            except Exception as err:
                log.error("unexpected watcher error: %s", err)
                time.sleep(self.poll_interval)

    def _process_window(self, from_block: int, to_block: int) -> bool:
        try:
            self._pull_factory_pairs(from_block, to_block)
            if self.track_mints:
                self._pull_known_mints(from_block, to_block)
            return True
        except RpcError as err:
            # Public BSC nodes (like ankr or bsc-dataseed) enforce 1000-5000 block limits or low compute budgets
            if "limit" in str(err).lower() or "range" in str(err).lower() or "response too large" in str(err).lower():
                self.current_chunk = max(10, self.current_chunk // 2)
                log.warning("rpc block range rejection, halved chunk to %d", self.current_chunk)
                return False
            log.warning("rpc error during sync [%d..%d]: %s", from_block, to_block, err)
            return False

    def _pull_factory_pairs(self, from_block: int, to_block: int):
        flt = build_pair_created_filter(self.factory_address, from_block, to_block)
        logs = self.rpc.get_logs(flt)
        for raw_log in logs:
            # print(f"DEBUG: raw log: {raw_log}")
            event = decode_pair_created(raw_log)
            if not event:
                continue
            is_new = self.storage.save_pair(
                pair_address=event.pair_address,
                token0=event.token0,
                token1=event.token1,
                block_number=event.block_number,
                tx_hash=event.tx_hash,
            )
            if is_new:
                self.notifier.notify_pair(event)

    def _pull_known_mints(self, from_block: int, to_block: int):
        # Check if recently tracked pairs received their initial LP inject
        recent_pairs = self.storage.get_recent_pairs(limit=200)
        if not recent_pairs:
            return
        addresses = [p["pair_address"] for p in recent_pairs]
        # TODO: split addresses list into slices of 50 if node complains about too many addresses
        flt = build_mint_filter(addresses, from_block, to_block)
        logs = self.rpc.get_logs(flt)
        for raw_log in logs:
            mint = decode_mint(raw_log)
            if not mint:
                continue
            # only alert if we haven't flagged mint for this pair yet
            if not self.storage.has_mint(mint.tx_hash, mint.pair_address):
                self.storage.record_mint(mint.tx_hash, mint.pair_address, mint.amount0, mint.amount1, mint.block_number)
                self.notifier.notify_mint(mint)

    def stop(self):
        self._running = False
