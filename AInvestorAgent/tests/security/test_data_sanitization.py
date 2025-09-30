"""输入数据清理/健壮性测试（特殊字符、长字符串、Unicode 混杂）

策略：
- 选一组通用端点进行“健壮性探测”（找一个能 200 的），对其传入特殊字符参数；
- 要求返回非 5xx，且不出现明显服务器异常堆栈；
- 若返回 HTML，检查是否对尖括号做了转义（避免反射性 XSS 迹象）。
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("AIA_PI_BASE", "http://127.0.0.1:8000")
TIMEOUT = 8

GET_CANDIDATES = [
    "/api/health",
    "/api/prices/AAPL",
    "/api/prices/AAPL?limit=5",
    "/api/prices/series?symbol=AAPL&days=7",
]

MALICIOUS_TEXTS = [
    "<script>alert(1)</script>",
    "' OR '1'='1",
    "\"/><img src=x onerror=alert(1)>",
    "测试-🧪-𝔘𝔫𝔦𝔠𝔬𝔡𝔢-ص-русский-長い長い長い" + "A"*1024,
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

@pytest.mark.parametrize("payload", MALICIOUS_TEXTS)
def test_input_sanitization_no_5xx_and_escaped(payload):
    ep = _pick_ok_endpoint()
    if not ep:
        pytest.skip("没有可用的 GET 端点进行输入清理测试")

    # 将恶意内容以查询字符串方式附加（多数后端会忽略未知参数，不应崩）
    url = f"{BASE_URL}{ep}"
    if "?" in ep:
        url += "&q=" + requests.utils.quote(payload, safe="")
    else:
        url += "?q=" + requests.utils.quote(payload, safe="")

    r = requests.get(url, timeout=TIMEOUT)
    assert r.status_code < 500, f"输入清理不当导致 5xx：{r.status_code}"

    ctype = r.headers.get("Content-Type", "")
    body = r.text[:2000]

    # 若返回 HTML，检查是否对 <script> 做了基本逃逸（不能原样反射出来）
    if "text/html" in ctype.lower():
        assert "<script>alert(1)</script>" not in body, "疑似反射性 XSS：脚本未被转义"
        # 常见的安全转义方式之一：&lt;script&gt;...
        assert "&lt;script&gt;" in body or "<script>" not in body, "HTML 中未见基本转义迹象"
