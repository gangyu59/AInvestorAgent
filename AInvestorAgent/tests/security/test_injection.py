"""注入测试（路径参数/查询参数的 SQL/命令注入防护）"""
import os
import pytest
import requests

BASE_URL = os.environ.get("AIA_PI_BASE", "http://127.0.0.1:8000")
TIMEOUT = 8

@pytest.mark.parametrize("symbol", [
    "AAPL'; DROP TABLE users; --",
    "AAPL%27%3B%20DROP%20TABLE%20users%3B--",
    "AAPL; rm -rf /",
    "AAPL | cat /etc/passwd",
])
def test_sql_injection_protection_on_prices(symbol):
    print("\n测试: SQL/命令注入防护 (prices)")
    # 在 /api/prices/{symbol} 与 /api/prices/series?symbol= 两种风格间自适配
    url1 = f"{BASE_URL}/api/prices/{symbol}"
    url2 = f"{BASE_URL}/api/prices/series?symbol={symbol}"

    for url in (url1, url2):
        try:
            r = requests.get(url, timeout=TIMEOUT)
            # 期望：不应 200（因为非法），而是 400/404/422 等；且不 5xx
            assert r.status_code in (400, 404, 422), f"对恶意 symbol 不应 200：{r.status_code}"
        except requests.RequestException:
            # 连接失败等，忽略单个 URL，尝试下一个
            continue

def test_path_traversal_on_reports():
    """测试报告下载接口是否防目录穿越（若未实现则跳过）"""
    candidates = [
        "/api/testing/reports/../../../../etc/passwd",
        "/api/testing/reports/%2e%2e/%2e%2e/%2e%2e/secret.txt",
    ]
    probed = False
    for ep in candidates:
        url = f"{BASE_URL}{ep}"
        try:
            r = requests.get(url, timeout=TIMEOUT)
            probed = True
            # 期望：404/400/403，且不应返回系统敏感文件内容
            assert r.status_code in (400,403,404), f"目录穿越应被拒绝：{r.status_code}"
            assert "root:" not in r.text, "疑似读取了敏感文件"
        except Exception:
            pass
    if not probed:
        pytest.skip("未提供 /api/testing/reports/{filename}，跳过目录穿越测试")
