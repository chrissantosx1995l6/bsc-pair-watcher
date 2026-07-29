import json
import logging
import time
import urllib.request
from typing import Any, Dict, List, Optional, Union

log = logging.getLogger(__name__)


class RpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(f"RPC error {code}: {message}")
        self.code = code
        self.message = message
        self.data = data


class RpcClient:
    """Barebones synchronous JSON-RPC wrapper tuned for high-churn EVM nodes."""

    def __init__(self, url: str, timeout: float = 12.0, max_retries: int = 5):
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries
        self._req_id = 0

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def raw_call(self, method: str, params: Optional[List[Any]] = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params if params is not None else [],
        }
        body = json.dumps(payload).encode("utf-8")

        backoff = 0.4
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    self.url,
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "bsc-watcher/0.2",
                    },
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                    # print(f"DEBUG: raw rpc resp {raw[:120]}")
                    data = json.loads(raw.decode("utf-8"))

                if "error" in data:
                    err = data["error"]
                    code = err.get("code", -1)
                    msg = err.get("message", "")
                    # BSC public nodes love throwing -32000 on rate limits instead of HTTP 429
                    if code in (-32000, -32005, 429) or "limit exceeded" in msg.lower():
                        log.warning("rpc throttled (%s), backoff %.1fs", msg, backoff)
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                    raise RpcError(code, msg, err.get("data"))

                return data.get("result")
            except urllib.error.HTTPError as http_err:
                if http_err.code in (429, 502, 503, 504):
                    log.warning("http %d from %s, retry in %.1fs", http_err.code, self.url, backoff)
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionResetError) as net_err:
                log.debug("net err attempt %d: %s", attempt, net_err)
                if attempt == self.max_retries:
                    raise
                time.sleep(backoff)
                backoff *= 1.8

        raise RuntimeError(f"rpc call {method} failed after {self.max_retries} attempts")

    def get_block_number(self) -> int:
        res = self.raw_call("eth_blockNumber")
        return int(res, 16)

    def get_logs(
        self,
        from_block: int,
        to_block: int,
        address: Union[str, List[str]],
        topics: Optional[List[Optional[Union[str, List[str]]]]] = None,
    ) -> List[Dict[str, Any]]:
        # BSC free RPC nodes cap response sizes to 5k-10k logs or small ranges.
        # If query fails due to range/size, split range in half and recurse.
        params: Dict[str, Any] = {
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
            "address": address,
        }
        if topics is not None:
            params["topics"] = topics

        try:
            res = self.raw_call("eth_getLogs", [params])
            return res if res is not None else []
        except RpcError as err:
            err_lower = err.message.lower()
            # quicknode / ankr / bsc-dataseed specifics
            is_range_issue = any(k in err_lower for k in ["limit exceeded", "more than", "block range", "response too large"])
            if is_range_issue and from_block < to_block:
                mid = (from_block + to_block) // 2
                log.info("log chunk %d-%d too big, splitting at %d", from_block, to_block, mid)
                left = self.get_logs(from_block, mid, address, topics)
                right = self.get_logs(mid + 1, to_block, address, topics)
                return left + right
            raise

    # FIXME: quicknode batch endpoint returns 200 with partial array errors if one subrequest fails
    def batch_call(self, calls: List[tuple[str, List[Any]]]) -> List[Any]:
        payload = []
        for method, params in calls:
            payload.append({
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": method,
                "params": params,
            })
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            responses = json.loads(resp.read().decode("utf-8"))

        # sort back by id because some rpc gateways return unordered batch responses
        responses.sort(key=lambda item: item.get("id", 0))
        return [item.get("result") for item in responses]
