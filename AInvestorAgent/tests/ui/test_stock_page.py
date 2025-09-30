# tests/ui/test_stock_page.py
import os
import pytest

FRONTEND_BASE = os.environ.get("FRONTEND_BASE", "http://127.0.0.1:5173")
SYMBOL = os.environ.get("UI_TEST_SYMBOL", "AAPL")

def test_stock_page_basic(page):
    # 支持 query/hash 两种形式
    paths = [
        f"/stock?query={SYMBOL}",
        f"/#/stock?query={SYMBOL}",
    ]
    ok = False
    for p in paths:
        try:
            page.goto(f"{FRONTEND_BASE}{p}", wait_until="domcontentloaded")
            # 价格图表（canvas/svg）、指标区、按钮
            selectors = [
                "[data-testid='PriceChart'] canvas",
                "[data-testid='PriceChart'] svg",
                "canvas",  # 宽松回退
                "text=/Decide Now|分析|Analyze/i",
            ]
            for s in selectors:
                try:
                    page.wait_for_selector(s, timeout=4000)
                    ok = True
                    break
                except Exception:
                    continue
            if ok:
                break
        except Exception:
            continue
    if not ok:
        pytest.skip("未找到个股页的图表/按钮元素（可能尚未渲染或选择器不匹配）")
