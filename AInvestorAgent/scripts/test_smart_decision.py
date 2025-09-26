# scripts/test_smart_decision.py
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 手动加载 .env 文件
ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)
    print(f"已加载环境变量文件: {ENV_FILE}")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.routers.decide import decide_now, DecideRequest


async def test_smart_decision():
    """测试智能决策系统"""
    print("🔄 测试智能决策系统...")

    # 检查环境变量是否正确加载
    print(f"DEEPSEEK_API_KEY: {'已设置' if os.getenv('DEEPSEEK_API_KEY') else '未设置'}")
    print(f"DOUBAO_API_KEY: {'已设置' if os.getenv('DOUBAO_API_KEY') else '未设置'}")

    request = DecideRequest(
        symbols=["AAPL", "MSFT", "NVDA"],
        topk=3,
        min_score=50,
        refresh_prices=False,
        use_llm=True
    )

    try:
        result = await decide_now(request)
        print(f"✅ 智能决策成功!")
        print(f"   方法: {result.method}")
        print(f"   选中: {len(result.holdings)} 只股票")

        if result.reasoning:
            print(f"   AI理由: {result.reasoning}")

        for holding in result.holdings:
            print(f"   {holding['symbol']}: {holding['weight'] * 100:.1f}%")

    except Exception as e:
        print(f"❌ 智能决策失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_smart_decision())