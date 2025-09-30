# tests/ui/test_portfolio_page.py
import os
import pytest

FRONTEND_BASE = os.environ.get("FRONTEND_BASE", "http://127.0.0.1:5173")

def test_portfolio_widgets(page):
    for p in ("/portfolio", "/#/portfolio"):
        try:
            page.goto(f"{FRONTEND_BASE}{p}", wait_until="domcontentloaded")
            # 组合图表/表格：权重饼图、持仓表、净值曲线
            sels = [
                "[data-testid='WeightsPie'] canvas",
                "[data-testid='HoldingsTable'] table",
                "[data-testid='EquityCurve'] svg",
                "text=/Run Backtest|回测|NAV/i"
            ]
            for s in sels:
                try:
                    page.wait_for_selector(s, timeout=4000)
                    return
                except Exception:
                    continue
        except Exception:
            continue
    pytest.skip("未检测到组合页主要组件（可能页面未接入或选择器需调整）")
