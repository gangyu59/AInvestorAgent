import time
import requests

def http_get_json(url: str, params: dict, retries: int = 3, backoff: float = 1.2, timeout: int = 20) -> dict:
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            if i < retries - 1:
                time.sleep(backoff * (i + 1))
    raise RuntimeError(str(last))
