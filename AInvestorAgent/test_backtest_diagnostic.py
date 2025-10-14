#!/usr/bin/env python3
"""
回测诊断脚本
用法: python test_backtest_diagnostic.py
"""
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any

API_BASE = "http://127.0.0.1:8000"


def print_section(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subsection(title: str):
    print(f"\n--- {title} ---")


def test_1_check_backend_health():
    """测试1: 检查后端健康状态"""
    print_section("测试 1: 后端健康检查")

    try:
        resp = requests.get(f"{API_BASE}/api/health", timeout=5)
        if resp.status_code == 200:
            print("✅ 后端服务正常运行")
            print(f"   响应: {resp.json()}")
        else:
            print(f"❌ 后端服务异常: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接后端: {e}")
        return False

    return True


def test_2_check_price_data():
    """测试2: 检查价格数据质量"""
    print_section("测试 2: 价格数据质量检查")

    test_symbols = ["AAPL", "MSFT", "NVDA"]
    results = {}

    for symbol in test_symbols:
        print_subsection(f"检查 {symbol}")

        try:
            resp = requests.get(
                f"{API_BASE}/api/prices/daily",
                params={"symbol": symbol, "limit": 260},
                timeout=10
            )

            if resp.status_code != 200:
                print(f"❌ API 错误: HTTP {resp.status_code}")
                results[symbol] = {"ok": False, "error": f"HTTP {resp.status_code}"}
                continue

            data = resp.json()

            # 解析数据
            if isinstance(data, dict) and "items" in data:
                items = data["items"]
            elif isinstance(data, list):
                items = data
            else:
                print(f"❌ 未知数据格式: {type(data)}")
                results[symbol] = {"ok": False, "error": "未知格式"}
                continue

            # 检查数据点数量
            print(f"   数据点数量: {len(items)}")

            if len(items) < 200:
                print(f"⚠️  数据不足 (需要至少 200 个交易日)")

            # 检查数据质量
            if len(items) > 0:
                first = items[0]
                last = items[-1]

                print(f"   最早日期: {first.get('date', 'N/A')}")
                print(f"   最新日期: {last.get('date', 'N/A')}")
                print(f"   第一个收盘价: {first.get('close', 'N/A')}")
                print(f"   最后收盘价: {last.get('close', 'N/A')}")

                # 检查是否有空值
                null_count = sum(1 for item in items if item.get('close') is None)
                if null_count > 0:
                    print(f"⚠️  发现 {null_count} 个空价格")

                # 检查日期连续性
                dates = [item.get('date', '') for item in items if item.get('date')]
                dates_sorted = sorted(dates)

                if dates != dates_sorted:
                    print(f"⚠️  日期未按时间顺序排列")

                # 采样检查
                if len(items) >= 5:
                    print(f"\n   前5个数据点:")
                    for i, item in enumerate(items[:5]):
                        print(f"     [{i}] {item.get('date')}: {item.get('close')}")

                    print(f"\n   后5个数据点:")
                    for i, item in enumerate(items[-5:]):
                        print(f"     [{len(items) - 5 + i}] {item.get('date')}: {item.get('close')}")

                results[symbol] = {
                    "ok": True,
                    "count": len(items),
                    "null_count": null_count,
                    "date_range": (first.get('date'), last.get('date'))
                }
                print(f"✅ {symbol} 价格数据正常")
            else:
                print(f"❌ {symbol} 无数据")
                results[symbol] = {"ok": False, "error": "无数据"}

        except Exception as e:
            print(f"❌ 异常: {e}")
            results[symbol] = {"ok": False, "error": str(e)}

    print_subsection("汇总")
    ok_count = sum(1 for r in results.values() if r.get("ok"))
    print(f"通过: {ok_count}/{len(test_symbols)}")

    return ok_count == len(test_symbols)


def test_3_check_latest_snapshot():
    """测试3: 检查最新组合快照"""
    print_section("测试 3: 最新组合快照检查")

    try:
        resp = requests.get(f"{API_BASE}/api/portfolio/snapshots/latest", timeout=10)

        if resp.status_code == 404:
            print("⚠️  暂无组合快照")
            print("   提示: 请先在 Portfolio 页面生成一个组合")
            return None

        if resp.status_code != 200:
            print(f"❌ API 错误: HTTP {resp.status_code}")
            return None

        snapshot = resp.json()

        print(f"✅ 找到快照: {snapshot.get('snapshot_id')}")
        print(f"   日期: {snapshot.get('as_of')}")
        print(f"   版本: {snapshot.get('version_tag')}")

        holdings = snapshot.get('holdings', [])
        print(f"   持仓数量: {len(holdings)}")

        if len(holdings) > 0:
            print(f"\n   持仓明细:")
            total_weight = 0.0
            for h in holdings:
                symbol = h.get('symbol', 'N/A')
                weight = h.get('weight', 0.0)
                sector = h.get('sector', 'N/A')
                score = h.get('score', 'N/A')
                total_weight += weight
                print(f"     {symbol:6s}  权重: {weight * 100:6.2f}%  行业: {sector:15s}  分数: {score}")

            print(f"\n   总权重: {total_weight * 100:.2f}%")

            if abs(total_weight - 1.0) > 0.01:
                print(f"⚠️  权重总和不等于 100%")
        else:
            print("❌ 快照无持仓数据")
            return None

        return snapshot

    except Exception as e:
        print(f"❌ 异常: {e}")
        return None


def test_4_run_backtest(snapshot: Dict[str, Any]):
    """测试4: 运行回测"""
    print_section("测试 4: 回测执行")

    if not snapshot:
        print("⚠️  跳过 (无快照数据)")
        return None

    holdings = snapshot.get('holdings', [])
    if not holdings:
        print("❌ 快照无持仓数据")
        return None

    # 准备回测请求
    weights = [
        {"symbol": h.get('symbol'), "weight": h.get('weight')}
        for h in holdings
    ]

    request_body = {
        "weights": weights,
        "window": "1Y",
        "trading_cost": 0.001,
        "rebalance": "weekly",
        "benchmark_symbol": "SPY"
    }

    print(f"发送回测请求:")
    print(f"  持仓数量: {len(weights)}")
    print(f"  窗口: 1Y")
    print(f"  基准: SPY")

    try:
        resp = requests.post(
            f"{API_BASE}/api/backtest/run",
            json=request_body,
            timeout=60
        )

        if resp.status_code != 200:
            print(f"❌ API 错误: HTTP {resp.status_code}")
            print(f"   响应: {resp.text[:500]}")
            return None

        result = resp.json()

        print(f"✅ 回测完成")

        # 检查结果结构
        dates = result.get('dates', [])
        nav = result.get('nav', [])
        benchmark_nav = result.get('benchmark_nav', [])
        drawdown = result.get('drawdown', [])
        metrics = result.get('metrics', {})
        debug_info = result.get('debug', {})

        print_subsection("数据维度")
        print(f"  日期数量: {len(dates)}")
        print(f"  NAV 数量: {len(nav)}")
        print(f"  基准 NAV 数量: {len(benchmark_nav)}")
        print(f"  回撤数量: {len(drawdown)}")

        # 检查日期范围
        if dates:
            print(f"\n  日期范围:")
            print(f"    开始: {dates[0]}")
            print(f"    结束: {dates[-1]}")
            print(f"    天数: {len(dates)}")

        # 检查 NAV 数据
        if nav:
            print(f"\n  NAV 数据检查:")
            print(f"    初始值: {nav[0]:.6f}")
            print(f"    最终值: {nav[-1]:.6f}")
            print(f"    最小值: {min(nav):.6f}")
            print(f"    最大值: {max(nav):.6f}")

            # 采样
            step = max(1, len(nav) // 10)
            print(f"\n    NAV 采样 (每 {step} 个点):")
            for i in range(0, len(nav), step):
                if i < len(dates):
                    print(f"      [{i:3d}] {dates[i]}: {nav[i]:.6f}")

            # 检查异常值
            if nav[0] > 0:
                changes = [nav[i] / nav[i - 1] - 1 for i in range(1, len(nav)) if nav[i - 1] > 0]
                if changes:
                    max_daily_change = max(abs(c) for c in changes)
                    print(f"\n    最大单日变化: {max_daily_change * 100:.2f}%")

                    if max_daily_change > 0.5:
                        print(f"    ⚠️  发现异常大的单日变化!")
                        # 找出异常点
                        for i in range(1, len(nav)):
                            if nav[i - 1] > 0:
                                change = nav[i] / nav[i - 1] - 1
                                if abs(change) > 0.5:
                                    date_str = dates[i] if i < len(dates) else "N/A"
                                    print(f"      [{i}] {date_str}: {change * 100:.2f}%")

        # 检查 Debug 信息
        if debug_info:
            print_subsection("Debug 信息")
            print(f"  使用的股票: {debug_info.get('used', [])}")
            print(f"  丢弃的股票: {debug_info.get('dropped', [])}")
            print(f"  日期总数: {debug_info.get('dates_cnt', 'N/A')}")

            symbols_info = debug_info.get('symbols', [])
            if symbols_info:
                print(f"\n  各股票数据点数量:")
                for s in symbols_info:
                    print(f"    {s.get('symbol', 'N/A')}: {s.get('points', 0)} 个点")

        # 检查指标
        print_subsection("性能指标")
        print(f"  年化收益: {metrics.get('ann_return', 0) * 100:.2f}%")
        print(f"  最大回撤: {metrics.get('max_dd', 0) * 100:.2f}%")
        print(f"  夏普比率: {metrics.get('sharpe', 0):.2f}")
        print(f"  胜率: {metrics.get('win_rate', 0) * 100:.2f}%")

        # 合理性检查
        print_subsection("合理性检查")
        issues = []

        if len(nav) < 100:
            issues.append(f"数据点太少 ({len(nav)} < 100)")

        if nav and nav[0] != 1.0:
            issues.append(f"初始 NAV 不为 1.0 (实际: {nav[0]})")

        ann_return = metrics.get('ann_return', 0)
        if abs(ann_return) > 2.0:
            issues.append(f"年化收益异常 ({ann_return * 100:.1f}%)")

        max_dd = metrics.get('max_dd', 0)
        if max_dd > 0.5:
            issues.append(f"最大回撤过大 ({max_dd * 100:.1f}%)")

        if nav:
            flat_count = sum(1 for i in range(1, len(nav)) if nav[i] == nav[i - 1])
            if flat_count > len(nav) * 0.5:
                issues.append(f"过多相同值 ({flat_count}/{len(nav)})")

        if issues:
            print("⚠️  发现以下问题:")
            for issue in issues:
                print(f"    • {issue}")
        else:
            print("✅ 所有指标看起来合理")

        return result

    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_5_compare_with_spy():
    """测试5: 对比 SPY 基准"""
    print_section("测试 5: SPY 基准对比")

    try:
        resp = requests.get(
            f"{API_BASE}/api/prices/daily",
            params={"symbol": "SPY", "limit": 260},
            timeout=10
        )

        if resp.status_code != 200:
            print(f"❌ 无法获取 SPY 数据: HTTP {resp.status_code}")
            return

        data = resp.json()

        if isinstance(data, dict) and "items" in data:
            items = data["items"]
        elif isinstance(data, list):
            items = data
        else:
            print(f"❌ 未知数据格式")
            return

        if len(items) < 200:
            print(f"⚠️  SPY 数据不足: {len(items)} 个点")
            return

        print(f"✅ SPY 数据正常: {len(items)} 个点")

        first = items[0]
        last = items[-1]

        print(f"   日期范围: {first.get('date')} 到 {last.get('date')}")
        print(f"   价格范围: {first.get('close')} 到 {last.get('close')}")

        if first.get('close') and last.get('close'):
            ret = (last['close'] / first['close'] - 1) * 100
            print(f"   期间收益: {ret:.2f}%")

    except Exception as e:
        print(f"❌ 异常: {e}")


def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "回测诊断工具 v1.0" + " " * 42 + "║")
    print("╚" + "=" * 78 + "╝")

    # 运行所有测试
    success = True

    # 测试1: 健康检查
    if not test_1_check_backend_health():
        print("\n❌ 后端服务不可用，终止测试")
        return

    # 测试2: 价格数据
    if not test_2_check_price_data():
        print("\n⚠️  价格数据有问题，但继续测试")
        success = False

    # 测试3: 快照
    snapshot = test_3_check_latest_snapshot()

    # 测试4: 回测
    backtest_result = test_4_run_backtest(snapshot)

    if not backtest_result:
        success = False

    # 测试5: SPY 基准
    test_5_compare_with_spy()

    # 最终总结
    print_section("测试总结")

    if success and backtest_result:
        print("✅ 所有测试通过")
        print("\n建议:")
        print("  • 回测数据看起来正常")
        print("  • 可以继续使用系统")
    else:
        print("❌ 发现问题")
        print("\n建议:")
        print("  • 检查上面标记为 ❌ 或 ⚠️ 的项目")
        print("  • 确保价格数据完整")
        print("  • 确保组合快照存在")
        print("  • 检查后端日志: backend/logs/")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()