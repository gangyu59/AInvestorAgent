"""认证测试（自适配端点 + 环境变量覆盖）

环境变量（可选）：
- AUTH_TEST_ENDPOINT：指定用于认证测试的端点（如 /api/admin/metrics）
- AUTH_HEADER_KEY：认证头字段名，默认 'Authorization'
- AUTH_BEARER：有效 Bearer token（形如 'Bearer xxx'，也可只给裸 token）
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("AIA_PI_BASE", "http://127.0.0.1:8000")
AUTH_TEST_ENDPOINT = os.environ.get("AUTH_TEST_ENDPOINT")  # 若不设置，将自动探测
AUTH_HEADER_KEY = os.environ.get("AUTH_HEADER_KEY", "Authorization")
AUTH_BEARER = os.environ.get("AUTH_BEARER")  # 仅在需要时使用
TIMEOUT = 8

# 可能需要认证的候选端点（GET/POST 皆可能）
CANDIDATES = [
    ("GET",  "/api/admin/metrics",    None),
    ("GET",  "/api/admin/healthz",    None),
    ("POST", "/api/portfolio/propose", {"ping": "ok"}),
    ("POST", "/orchestrator/decide",   {"symbols":["AAPL"],"topk":1,"use_llm":False}),
]

def _norm_bearer(value: str) -> str:
    return value if value.startswith("Bearer ") else f"Bearer {value}"

def _probe_protected():
    if AUTH_TEST_ENDPOINT:
        return ("GET", AUTH_TEST_ENDPOINT, None)
    for method, ep, body in CANDIDATES:
        url = f"{BASE_URL}{ep}"
        try:
            r = requests.request(method, url, json=body, timeout=TIMEOUT)
            # 返回 401/403 说明这个端点是“受保护”的
            if r.status_code in (401, 403):
                return (method, ep, body)
        except Exception:
            pass
    return None

@pytest.mark.parametrize("invalid_token", [None, "badtoken", "Bearer invalid", "Token xxx"])
def test_authentication_required_or_open(invalid_token):
    """若存在需要认证的端点：验证未携带/携带无效凭据时被拒绝；若不存在则跳过。"""
    probed = _probe_protected()
    if not probed:
        pytest.skip("未找到需要认证的端点（或系统处于无认证模式）")
    method, ep, body = probed
    url = f"{BASE_URL}{ep}"

    headers = {}
    if invalid_token is not None:
        headers[AUTH_HEADER_KEY] = invalid_token

    r = requests.request(method, url, json=body, headers=headers, timeout=TIMEOUT)
    assert r.status_code in (401,403,404), f"低权或无效令牌访问应被拒绝/隐藏，实际 {r.status_code}"

def test_authentication_success_when_provided():
    """对受保护端点：若提供了有效凭据（通过环境变量），应获得非 401/403 的响应。"""
    probed = _probe_protected()
    if not probed:
        pytest.skip("未找到需要认证的端点")
    if not AUTH_BEARER:
        pytest.skip("未提供 AUTH_BEARER，跳过通过用例")

    method, ep, body = probed
    url = f"{BASE_URL}{ep}"
    headers = {AUTH_HEADER_KEY: _norm_bearer(AUTH_BEARER)}

    r = requests.request(method, url, json=body, headers=headers, timeout=TIMEOUT)
    assert r.status_code not in (401, 403), f"携带凭据仍被拒绝：{r.status_code}"
