# scripts/test_technical_analysis.py
# !/usr/bin/env python3
import sys
from pathlib import Path

# 添加后端路径
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.storage.db import SessionLocal
from backend.factors.momentum import calculate_technical_indicators
from backend.factors.risk import calculate_risk_metrics
from datetime import date


def test_technical_indicators():
    """测试技术指标计算"""
    symbols = ["AAPL", "MSFT", "TSLA", "SPY"]

    with SessionLocal() as db:
        for symbol in symbols:
            print(f"\n=== 测试 {symbol} ===")

            try:
                # 测试技术指标
                tech_indicators = calculate_technical_indicators(db, symbol, date.today())
                print(f"技术指标: {len(tech_indicators)} 个")
                for key, value in tech_indicators.items():
                    if isinstance(value, float):
                        print(f"  {key}: {value:.4f}")
                    else:
                        print(f"  {key}: {value}")

                # 测试风险指标
                risk_metrics = calculate_risk_metrics(db, symbol, date.today())
                print(f"风险指标: {len(risk_metrics)} 个")
                for key, value in risk_metrics.items():
                    if isinstance(value, float):
                        print(f"  {key}: {value:.4f}")
                    else:
                        print(f"  {key}: {value}")

            except Exception as e:
                print(f"  错误: {e}")


if __name__ == "__main__":
    test_technical_indicators()