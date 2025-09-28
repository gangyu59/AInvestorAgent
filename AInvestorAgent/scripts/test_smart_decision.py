#!/usr/bin/env python3
import sys
from pathlib import Path

# 添加后端路径
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 加载环境变量
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import asyncio
from backend.storage.db import SessionLocal
from backend.agents.signal_researcher import EnhancedSignalResearcher
from backend.agents.portfolio_manager import EnhancedPortfolioManager
from datetime import date


async def test_smart_decision():
    """测试智能决策流程"""
    symbols = ["AAPL", "MSFT", "TSLA", "NVDA"]

    print("=== 开始智能股票分析 ===")

    with SessionLocal() as db:
        # 第一步：分析每只股票
        analyses = {}
        researcher = EnhancedSignalResearcher()

        for symbol in symbols:
            print(f"\n分析 {symbol}...")

            ctx = {
                "symbol": symbol,
                "db_session": db,
                "asof": date.today(),
                "fundamentals": {"pe": 25, "roe": 15},  # 模拟基本面数据
                "news_raw": [{"title": f"{symbol}季度业绩超预期", "summary": "公司表现强劲"}]
            }

            try:
                analysis = await researcher.analyze_with_technical_indicators(ctx)
                analyses[symbol] = analysis

                # 显示分析结果
                if analysis.get("ok"):
                    print(f"  综合评分: {analysis.get('adjusted_score', analysis.get('score', 0))}")

                    tech = analysis.get("technical_indicators", {})
                    print(
                        f"  技术指标: RSI={tech.get('rsi', 0):.1f} MA趋势={'上升' if tech.get('ma5', 0) > tech.get('ma20', 0) else '下降'}")

                    llm = analysis.get("llm_analysis", {})
                    print(f"  AI建议: {llm.get('recommendation', 'N/A')} (信心:{llm.get('confidence', 'N/A')})")
                    print(f"  投资逻辑: {llm.get('logic', 'N/A')}")
                else:
                    print(f"  分析失败: {analysis}")

            except Exception as e:
                print(f"  错误: {e}")
                analyses[symbol] = {"ok": False, "score": 0}

        # 第二步：智能组合构建
        print(f"\n=== 构建投资组合 ===")
        pm = EnhancedPortfolioManager()

        try:
            portfolio_result = await pm.smart_allocate(analyses)

            if portfolio_result.get("ok"):
                print("推荐组合:")
                for holding in portfolio_result.get("weights", []):
                    symbol = holding["symbol"]
                    weight = holding["weight"]
                    analysis = analyses.get(symbol, {})
                    score = analysis.get("adjusted_score", analysis.get("score", 0))
                    print(f"  {symbol}: {weight * 100:.1f}% (评分:{score})")

                reasoning = portfolio_result.get("reasoning", "")
                if reasoning:
                    print(f"\n选择理由: {reasoning}")

            else:
                print("组合构建失败")

        except Exception as e:
            print(f"组合构建错误: {e}")


if __name__ == "__main__":
    asyncio.run(test_smart_decision())