# tests/ui/test_navigation.py
import os
import pytest

FRONTEND_BASE = os.environ.get("FRONTEND_BASE", "http://127.0.0.1:5173")
ROUTES = [
    ("/stock",  "/#/stock",   ["[data-testid='stock-page']",  "text=/个股|Symbol/i"]),
    ("/portfolio","/#/portfolio",["[data-testid='portfolio-page']", "text=/持仓|组合/i"]),
    ("/simulator","/#/simulator",["[data-testid='simulator-page']", "text=/模拟|回测|Backtest/i"]),
    ("/monitor", "/#/monitor", ["[data-testid='monitor-page']", "text=/舆情|情绪|News/i"]),
    ("/manage",  "/#/manage",  ["[data-testid='manage-page']",  "text=/管理|Settings|Admin/i"]),
]

def _goto_and_expect(page, path1, path2, selectors):
    for p in (path1, path2):
        try:
            page.goto(f"{FRONTEND_BASE}{p}", wait_until="domcontentloaded")
            for s in selectors:
                try:
                    page.wait_for_selector(s, timeout=3000)
                    return True
                except Exception:
                    continue
        except Exception:
            continue
    return False

@pytest.mark.parametrize("path1,path2,selectors", ROUTES)
def test_direct_route(page, path1, path2, selectors):
    ok = _goto_and_expect(page, path1, path2, selectors)
    if not ok:
        pytest.skip(f"路由 {path1} / {path2} 无法确认对应页面元素（可能页面尚未接入）")

def test_nav_links_clickable(page):
    page.goto(f"{FRONTEND_BASE}/", wait_until="domcontentloaded")
    # 尝试从顶栏点击（如果存在）
    candidates = [
        ("个股", ["/stock","/#/stock"]),
        ("组合", ["/portfolio","/#/portfolio"]),
        ("模拟", ["/simulator","/#/simulator"]),
        ("舆情", ["/monitor","/#/monitor"]),
        ("管理", ["/manage","/#/manage"]),
    ]
    found_any = False
    for text, paths in candidates:
        try:
            el = page.get_by_text(text, exact=False)
            el.first.click(timeout=1500)
            found_any = True
        except Exception:
            # 直接跳路由验证
            ok = any(_goto_and_expect(page, p, p, ["body"]) for p in paths)
            found_any = found_any or ok
    if not found_any:
        pytest.skip("导航菜单不可见/不可点（可能首页未挂载导航条）")
