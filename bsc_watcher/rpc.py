import json
import logging
import time
import urllib.request
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


class RpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(f"RPC error {code}: {message}")
        self.code = code
        self.message = message
        self.data = data


class RpcClient:
    def __init__(self, url: str, timeout: float = 10.0, max_retries: int = 3):
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries
        self._req_id = 0

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def call(self, method: str, params: Optional[List[Any]] = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or [],
        }
        raw_body = json.dumps(payload).encode("utf-8")

        last_exc = None
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(
                    self.url,
                    data=raw_body,
                    headers={"Content-Type": "application/json", "User-Agent": "bsc-watcher/0.1"},
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                if "error" in data:
                    err = data["error"]
                    raise RpcError(err.get("code", -1), err.get("message", "unknown"), err.get("data"))
                return data.get("result")
            except Exception as exc:
                last_exc = exc
                log.debug("rpc call %s attempt %d failed: %s", method, attempt + 1, exc)
                time.sleep(0.5 * (2 ** attempt))

        raise RuntimeError(f"rpc call {method} failed after {self.max_retries} attempts") from last_exc

    def get_block_number(self) -> int:
        res = self.call("eth_blockNumber")
        return int(res, 16)

    def get_logs(self, from_block: int, to_block: int, address: Any, topics: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
            "address": address,
        }
        if topics:
            params["topics"] = topics
        res = self.call("eth_getLogs", [params])
        return res or []
