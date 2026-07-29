import re
from dataclasses import dataclass
from typing import Optional, Set, Tuple

# WBNB, BUSD, USDT, USDC, DAI, ETH on BSC mainnet
KNOWN_QUOTE_TOKENS = {
    "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c": ("WBNB", 18),
    "0xe9e7cea3dedca5984780bafc599bd69add087d56": ("BUSD", 18),
    "0x55d398326f99059ff775485246999027b3197955": ("USDT", 18),
    "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d": ("USDC", 18),
    "0x1af3f329e8be154074d8769d1ffa4ee058b1dbc3": ("DAI", 18),
    "0x2170ed0880ac9a755fd29b2688956bd959f933f8": ("ETH", 18),
}

# Quick suspicious patterns in token symbols or names
SUSPICIOUS_NAME_PATTERNS = [
    re.compile(r"claim\s*at", re.IGNORECASE),
    re.compile(r"airdrop", re.IGNORECASE),
    re.compile(r"visit\s*https?:", re.IGNORECASE),
    re.compile(r"\bwww\.", re.IGNORECASE),
    re.compile(r"\.org\b", re.IGNORECASE),
    re.compile(r"\.io\b", re.IGNORECASE),
    re.compile(r"\.finance\b", re.IGNORECASE),
]

# Standard dead / burn sinks
DEAD_ADDRESSES = {
    "0x0000000000000000000000000000000000000000",
    "0x000000000000000000000000000000000000dead",
}

@dataclass
class FilterConfig:
    min_liquidity_bnb: float = 0.5
    min_liquidity_usd: float = 200.0
    quote_only: bool = True
    ignore_blacklisted: bool = True
    drop_scam_names: bool = True
    # ignore tiny dust pairs deployed to pollute factory log indexers
    min_raw_reserve: int = 10**14


class PairFilter:
    def __init__(self, config: FilterConfig, blacklisted_tokens: Optional[Set[str]] = None):
        self.config = config
        self.blacklisted = {a.lower() for a in (blacklisted_tokens or set())}

    def is_quote_token(self, token_address: str) -> bool:
        return token_address.lower() in KNOWN_QUOTE_TOKENS

    def get_quote_info(self, token0: str, token1: str) -> Tuple[Optional[str], Optional[str], Optional[Tuple[str, int]]]:
        t0 = token0.lower()
        t1 = token1.lower()
        if t0 in KNOWN_QUOTE_TOKENS:
            return t0, t1, KNOWN_QUOTE_TOKENS[t0]
        if t1 in KNOWN_QUOTE_TOKENS:
            return t1, t0, KNOWN_QUOTE_TOKENS[t1]
        return None, None, None

    def is_suspicious_text(self, name: str, symbol: str) -> bool:
        if not self.config.drop_scam_names:
            return False
        target = f"{name} {symbol}"
        for pattern in SUSPICIOUS_NAME_PATTERNS:
            if pattern.search(target):
                return True
        return False

    def passes_preliminary(self, token0: str, token1: str) -> bool:
        t0 = token0.lower()
        t1 = token1.lower()

        if t0 == t1 or t0 in DEAD_ADDRESSES or t1 in DEAD_ADDRESSES:
            return False

        if self.config.ignore_blacklisted:
            if t0 in self.blacklisted or t1 in self.blacklisted:
                return False

        if self.config.quote_only:
            quote, target, _ = self.get_quote_info(t0, t1)
            if not quote:
                return False

        return True

    def passes_liquidity(self, reserve0: int, reserve1: int, quote_is_token0: bool, bnb_usd_price: float = 300.0) -> bool:
        # FIXME: token decimals default to 18 if rpc fails; should cache decimals properly
        quote_reserve = reserve0 if quote_is_token0 else reserve1
        if quote_reserve < self.config.min_raw_reserve:
            return False

        # print(f"DEBUG reserve check: {quote_reserve} vs {self.config.min_raw_reserve}")
        # Standardize quote reserve value (assuming 18 decimals for WBNB / standard stables)
        human_quote = quote_reserve / 1e18
        if human_quote < self.config.min_liquidity_bnb:
            return False

        return True

    def add_to_blacklist(self, token_address: str):
        self.blacklisted.add(token_address.lower())
