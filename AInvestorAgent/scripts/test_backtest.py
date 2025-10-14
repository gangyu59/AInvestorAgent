#!/usr/bin/env python3
"""测试回测功能"""
import requests
import json
import sys

print("=" * 60)
print("🔄 运行回测")
print("=" * 60)

# 方案1: 使用刚生成的组合（从test_portfolio_result.json读取）
print("\n📂 从最新生成的组合读取...")

try:
    with open('test_portfolio_result.json', 'r', encoding='utf-8') as f:
        portfolio = json.load(f)

    holdings = portfolio.get('holdings', [])

    if not holdings:
        print("❌ test_portfolio_result.json 中没有持仓数据")
        sys.exit(1)

    print(f"✅ 读取到 {len(holdings)} 只持仓")

    # 显示持仓
    print("\n持仓列表:")
    for h in holdings:
        print(f"  {h['symbol']}: {h['weight']:.2%}")

except FileNotFoundError:
    print("❌ 找不到 test_portfolio_result.json")
    print("💡 请先运行: python scripts/test_propose.py")
    sys.exit(1)

# 构建回测请求
backtest_data = {
    "holdings": holdings,
    "window": "1Y",
    "cost": 0.001,
    "rebalance": "weekly",
    "max_trades_per_week": 3
}

print(f"\n回测参数:")
print(f"  窗口: {backtest_data['window']}")
print(f"  成本: {backtest_data['cost']}")
print(f"  调仓频率: {backtest_data['rebalance']}")
print(f"  每周最多调仓: {backtest_data['max_trades_per_week']}次")

print("\n🚀 发送回测请求...")

try:
    resp = requests.post(
        "http://localhost:8000/api/backtest/run",
        json=backtest_data,
        timeout=60
    )

    if resp.status_code == 200:
        result = resp.json()

        print("\n✅ 回测完成")
        print("=" * 60)

        # 显示指标
        metrics = result.get('metrics', {})
        print("\n📊 回测指标:")
        print(f"  年化收益: {metrics.get('ann_return', 0):.2%}")
        print(f"  Sharpe: {metrics.get('sharpe', 0):.2f}")
        print(f"  最大回撤: {metrics.get('max_dd', 0):.2%}")
        print(f"  胜率: {metrics.get('win_rate', 0):.2%}")

        # 显示净值曲线
        dates = result.get('dates', [])
        nav = result.get('nav', [])
        benchmark_nav = result.get('benchmark_nav', [])

        print(f"\n📈 净值数据:")
        print(f"  数据点数: {len(dates)}")

        if nav:
            print(f"  起始净值: {nav[0]:.4f}")
            print(f"  最终净值: {nav[-1]:.4f}")
            print(f"  累计收益: {(nav[-1] / nav[0] - 1):.2%}")

        if benchmark_nav:
            print(f"\n  基准起始: {benchmark_nav[0]:.4f}")
            print(f"  基准最终: {benchmark_nav[-1]:.4f}")
            print(f"  基准收益: {(benchmark_nav[-1] / benchmark_nav[0] - 1):.2%}")

            if nav:
                alpha = (nav[-1] / nav[0] - 1) - (benchmark_nav[-1] / benchmark_nav[0] - 1)
                print(f"  超额收益: {alpha:.2%}")

        # 保存结果
        with open('test_backtest_result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("\n💾 完整结果已保存到: test_backtest_result.json")

        print("\n" + "=" * 60)
        print("✅ 回测测试通过！")

    elif resp.status_code == 422:
        print(f"\n❌ 参数验证失败")
        print(f"错误信息: {resp.text}")

        # 尝试打印详细错误
        try:
            error_detail = resp.json()
            print("\n详细错误:")
            print(json.dumps(error_detail, indent=2, ensure_ascii=False))
        except:
            pass
    else:
        print(f"\n❌ 回测失败: HTTP {resp.status_code}")
        print(f"响应: {resp.text[:500]}")

except requests.Timeout:
    print("\n❌ 请求超时（>60秒）")
    print("💡 回测可能需要更长时间，可以增加timeout")
except Exception as e:
    print(f"\n❌ 请求出错: {e}")
    import traceback

    traceback.print_exc()