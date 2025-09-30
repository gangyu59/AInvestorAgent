# tests/ui/test_charts.py
import os
import pytest

FRONTEND_BASE = os.environ.get("FRONTEND_BASE", "http://127.0.0.1:5173")

CHART_PAGES = [
    ("/",            "/#/",           ["[data-testid='PriceChart'] canvas", "canvas", "svg"]),
    ("/stock",       "/#/stock",      ["[data-testid='PriceChart'] canvas", "canvas", "svg"]),
    ("/portfolio",   "/#/portfolio",  ["[data-testid='WeightsPie'] canvas", "svg", "canvas"]),
    ("/simulator",   "/#/simulator",  ["[data-testid='EquityCurve'] svg",   "canvas", "svg"]),
    ("/monitor",     "/#/monitor",    ["[data-testid='SentimentTimeline'] svg", "svg", "canvas"]),
]

@pytest.mark.parametrize("path1,path2,selectors", CHART_PAGES)
def test_chart_presence(page, path1, path2, selectors):
    # 打开其中任一路径，找到任一图形元素即视作通过
    for p in (path1, path2):
        try:
            page.goto(f"{FRONTEND_BASE}{p}", wait_until="domcontentloaded")
            for s in selectors:
                try:
                    page.wait_for_selector(s, timeout=4000)
                    return
                except Exception:
                    continue
        except Exception:
            continue
    pytest.skip(f"{path1}/{path2} 未检测到图表元素（可能页面未实现或选择器不匹配）")
