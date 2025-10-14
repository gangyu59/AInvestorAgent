#!/usr/bin/env python3
"""测试组合生成"""
import requests
import json

url = "http://localhost:8000/api/portfolio/propose"
data = {
    "symbols": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "TSLA", "AMZN", "NFLX"]
}

print("🚀 发送组合建议请求...")
print(f"股票池: {data['symbols']}\n")

try:
    response = requests.post(url, json=data, timeout=30)

    if response.status_code == 200:
        result = response.json()

        print("✅ 组合生成成功！\n")
        print("=" * 60)

        holdings = result.get('holdings', [])
        if holdings:
            print(f"📊 持仓明细 (共{len(holdings)}只):")
            for h in holdings:
                symbol = h.get('symbol', '?')
                weight = h.get('weight', 0)
                score = h.get('score', 0)
                reasons = h.get('reasons', [])

                print(f"\n  {symbol}:")
                print(f"    权重: {weight:.2%}")
                print(f"    评分: {score:.2f}")
                if reasons:
                    print(f"    理由: {', '.join(reasons[:2])}")
        else:
            print("⚠️ 返回的holdings是空的")

        print("\n" + "=" * 60)
        print(f"快照ID: {result.get('snapshot_id', 'N/A')}")
        print(f"版本: {result.get('version_tag', 'N/A')}")
        print(f"时间: {result.get('as_of', 'N/A')}")

        # 保存完整结果
        with open('test_portfolio_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("\n💾 完整结果已保存到: test_portfolio_result.json")

    else:
        print(f"❌ 请求失败: {response.status_code}")
        print(f"错误信息: {response.text[:500]}")

except Exception as e:
    print(f"❌ 请求出错: {e}")