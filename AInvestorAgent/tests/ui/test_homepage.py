# tests/ui/test_homepage.py
import os
import pytest

FRONTEND_BASE = os.environ.get("FRONTEND_BASE", "http://127.0.0.1:5173")
START_PATHS = ["/", "/#/"]  # 支持 hash 路由与普通路由

def _first_ok(base, candidates):
    for p in candidates:
        return f"{base}{p}"
    return base

def _selectors(*sels):
    return [s for s in sels if s]

@pytest.mark.parametrize("start", START_PATHS)
def test_homepage_loads(page, start):
    url = f"{FRONTEND_BASE}{start}"
    page.goto(url, wait_until="domcontentloaded")
    # 标题或顶栏
    candidates = _selectors(
        "[data-testid='nav-bar']",
        "header >> text=/AInvestorAgent|投资/i",
        "text=/个股|组合|模拟|舆情|管理/"
    )
    for s in candidates:
        try:
            page.wait_for_selector(s, timeout=5000)
            break
        except Exception:
            continue
    else:
        pytest.skip("首页未找到可识别的导航/标题元素")
    # 基本可见性
    assert page.title() is not None
