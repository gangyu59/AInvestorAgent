"""XSS 测试（反射型 & 基础输出编码）

策略：
- 向常见 GET 端点注入 script 片段作为查询参数；
- 要求：不 5xx；如返回 HTML，不应原样反射脚本片段（应转义）。
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("AIA_PI_BASE", "http://127.0.0.1:8000")
TIMEOUT = 8

GET_CANDIDATES = [
    "/api/health",
    "/api/prices/AAPL",
    "/api/prices/series?symbol=AAPL&days=7",
]

XSS_PAYLOADS = [
    "<script>alert('xss')</script>",
    "<IMG SRC=x onerror=alert(1)>",
    "<svg/onload=alert(1)>",
]

def _pick_ok_endpoint():
    for ep in GET_CANDIDATES:
        try:
            r = requests.get(f"{BASE_URL}{ep}", timeout=TIMEOUT)
            if r.status_code == 200:
                return ep
        except Exception:
            pass
    return None

@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_reflected_xss_not_rendered(payload):
    ep = _pick_ok_endpoint()
    if not ep:
        pytest.skip("没有可用的 GET 端点用于 XSS 测试")

    if "?" in ep:
        url = f"{BASE_URL}{ep}&q={requests.utils.quote(payload, safe='')}"
    else:
        url = f"{BASE_URL}{ep}?q={requests.utils.quote(payload, safe='')}"

    r = requests.get(url, timeout=TIMEOUT)
    assert r.status_code < 500, f"输入导致 5xx：{r.status_code}"

    ctype = (r.headers.get("Content-Type") or "").lower()
    body = r.text[:2000]

    # 若返回 HTML，应不含原样的 <script> 或危险 on* 属性
    if "text/html" in ctype:
        assert "<script" not in body.lower(), "疑似反射型 XSS：脚本标签被原样输出"
        assert "onerror=" not in body.lower(), "疑似反射型 XSS：事件处理器被原样输出"
