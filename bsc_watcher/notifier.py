import logging
import httpx
from typing import Optional
from bsc_watcher.events import PairCreated, MintEvent

log = logging.getLogger("bsc_watcher.notifier")


def _fmt_amt(val: int, decimals: int = 18) -> str:
    if val == 0:
        return "0"
    raw = str(val).zfill(decimals + 1)
    int_part = raw[:-decimals] or "0"
    dec_part = raw[-decimals:].rstrip("0")
    if not dec_part:
        return int_part
    return f"{int_part}.{dec_part[:6]}"


class Notifier:
    """Formats and sends notifications to stdout and optional Telegram bot."""

    def __init__(self, telegram_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.tg_token = telegram_token
        self.chat_id = chat_id
        self._disabled = False
        self._client = httpx.Client(timeout=8.0) if telegram_token and chat_id else None

    def notify_pair(self, event: PairCreated):
        text = (
            f"*NEW PAIR DEPLOYED*\n"
            f"Pair: `{event.pair_address}`\n"
            f"T0: `{event.token0}`\n"
            f"T1: `{event.token1}`\n"
            f"Block: `{event.block_number}`\n"
            f"Tx: [bscscan](https://bscscan.com/tx/{event.tx_hash})"
        )
        print(f"\n[+] PAIR: {event.token0} / {event.token1} -> {event.pair_address} (block {event.block_number})")
        self._send_tg(text)

    def notify_mint(self, event: MintEvent, sym0: str = "T0", sym1: str = "T1", dec0: int = 18, dec1: int = 18):
        a0_str = _fmt_amt(event.amount0, dec0)
        a1_str = _fmt_amt(event.amount1, dec1)
        text = (
            f"*LIQUIDITY ADDED*\n"
            f"Pair: `{event.pair_address}`\n"
            f"{sym0}: `{a0_str}`\n"
            f"{sym1}: `{a1_str}`\n"
            f"Tx: [bscscan](https://bscscan.com/tx/{event.tx_hash})"
        )
        print(f"[$] MINT: {a0_str} {sym0} + {a1_str} {sym1} into {event.pair_address}")
        self._send_tg(text)

    def _send_tg(self, msg: str):
        if not self._client or self._disabled or not self.tg_token or not self.chat_id:
            return
        url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
        try:
            resp = self._client.post(url, json={
                "chat_id": self.chat_id,
                "text": msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            })
            if resp.status_code == 401:
                log.error("telegram bot token rejected (401), disabling tg alerts")
                self._disabled = True
            elif resp.status_code != 200:
                log.warning("telegram send error %d: %s", resp.status_code, resp.text)
        except httpx.RequestError as exc:
            log.warning("telegram unreachable: %s", exc)

    def close(self):
        if self._client:
            self._client.close()
