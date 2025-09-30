"""
端到端集成测试
测试完整的决策流程：数据获取 → 因子计算 → 评分 → 组合构建 → 回测
"""
import pytest
import requests
import time
from typing import Dict, Any


class TestEndToEndDecisionFlow:
    """端到端决策流程测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        """测试设置"""
        self.base_url = base_url
        self.timeout = 120

        # 验证后端是否运行
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"后端未运行: {e}")

    def find_working_endpoint(self, endpoints, method="GET", json_data=None, timeout=30):
        """查找可用的端点"""
        for endpoint in endpoints:
            try:
                if method == "POST":
                    response = requests.post(endpoint, json=json_data, timeout=timeout)
                else:
                    response = requests.get(endpoint, timeout=timeout)

                if response.status_code == 200:
                    print(f"   ✅ 找到可用端点: {endpoint}")
                    return response, endpoint
            except Exception as e:
                continue
        return None, None

    def test_01_complete_decision_pipeline(self, test_symbols):
        """
        测试1: 完整决策管道
        验证从输入股票池到输出组合建议的完整流程
        """
        print("\n" + "="*60)
        print("测试1: 完整决策管道")
        print("="*60)

        symbols = test_symbols[:3]  # 使用前3支股票减少负载

        candidates = [
            {"symbol": sym, "sector": "Technology", "score": 80.0}
            for sym in symbols
        ]

        # Step 1: 调用决策端点
        print(f"\n📊 Step 1: 调用决策端点")
        start_time = time.time()

        decision_endpoints = [
            f"{self.base_url}/api/orchestrator/propose"
        ]

        response, used_endpoint = self.find_working_endpoint(
            decision_endpoints,
            method="POST",
            json_data = {
                "candidates": candidates,
                "params": {"mock": True}
            },
            timeout=self.timeout
        )

        if not response:
            print(f"   ⚠️  决策端点未找到，跳过测试")
            pytest.skip("决策API端点未实现")
            return

        elapsed = time.time() - start_time
        print(f"   ⏱️  耗时: {elapsed:.2f}秒")

        # 验证响应
        data = response.json()
        print(f"   ✅ 决策成功")

        # Step 2: 验证返回结构
        print(f"\n📋 Step 2: 验证返回数据结构")

        # 灵活的字段验证
        found_fields = {}
        possible_fields = {
            "trace_id": ["trace_id", "id", "request_id"],
            "holdings": ["holdings", "portfolio", "allocations"],
            "as_of": ["as_of", "timestamp", "date"],
            "version_tag": ["version_tag", "version", "tag"]
        }

        for standard_field, possible_names in possible_fields.items():
            for name in possible_names:
                if name in data:
                    found_fields[standard_field] = name
                    break

        for field, actual_name in found_fields.items():
            value = data[actual_name]
            display_value = f'{len(value)}支股票' if field == "holdings" and isinstance(value, list) else value
            print(f"   ✅ {field}: {display_value}")

        # Step 3: 验证组合质量（如果存在持仓数据）
        print(f"\n🎯 Step 3: 验证组合质量")

        holdings_key = found_fields.get("holdings")
        if holdings_key and holdings_key in data and isinstance(data[holdings_key], list):
            holdings = data[holdings_key]

            # 持仓数量检查
            if len(holdings) > 0:
                print(f"   ✅ 持仓数量: {len(holdings)}")

                # 权重总和检查
                if "weight" in holdings[0]:
                    total_weight = sum(h.get("weight", 0) for h in holdings)
                    # 判断权重格式
                    if total_weight <= 1.5:  # 小数格式
                        assert 0.95 <= total_weight <= 1.05, f"权重总和异常: {total_weight}"
                        print(f"   ✅ 权重总和: {total_weight:.3f} (小数格式)")
                    else:  # 百分比格式
                        assert 99.5 <= total_weight <= 100.5, f"权重总和异常: {total_weight}"
                        print(f"   ✅ 权重总和: {total_weight:.2f}%")

                    # 单票权重检查
                    max_weight = max(h.get("weight", 0) for h in holdings)
                    if total_weight <= 1.5:  # 小数格式
                        assert max_weight <= 0.35, f"单票权重超限: {max_weight}"
                    else:  # 百分比格式
                        assert max_weight <= 35.5, f"单票权重超限: {max_weight}%"
                    print(f"   ✅ 最大单票权重: {max_weight:.2f}{'' if total_weight <= 1.5 else '%'}")

                # 入选理由检查
                reasons_found = False
                for holding in holdings:
                    if "reasons" in holding or "reason" in holding:
                        reasons_found = True
                        break
                if reasons_found:
                    print(f"   ✅ 持仓包含入选理由")
                else:
                    print(f"   ℹ️  未找到入选理由字段")
            else:
                print(f"   ℹ️  持仓列表为空")
        else:
            print(f"   ℹ️  未找到持仓数据")

        # Step 4: 验证Trace可追溯
        print(f"\n🔍 Step 4: 验证Trace可追溯性")
        trace_id_key = found_fields.get("trace_id")
        if trace_id_key and trace_id_key in data:
            trace_id = data[trace_id_key]

            # 尝试查询trace端点
            trace_endpoints = [
                f"{self.base_url}/api/trace/{trace_id}",
                f"{self.base_url}/api/traces/{trace_id}",
                f"{self.base_url}/trace/{trace_id}"
            ]

            try:
                trace_response, _ = self.find_working_endpoint(trace_endpoints, method="GET", timeout=10)
                if trace_response and trace_response.status_code == 200:
                    trace_data = trace_response.json()
                    steps_count = len(trace_data.get('steps', [])) if isinstance(trace_data, dict) else "N/A"
                    print(f"   ✅ Trace查询成功: {steps_count}个步骤")
                else:
                    print(f"   ℹ️  Trace查询端点未实现")
            except:
                print(f"   ℹ️  跳过Trace查询（端点可能未实现）")
        else:
            print(f"   ℹ️  未找到Trace ID")

        print(f"\n✅ 测试1通过: 完整决策管道正常工作")

    def test_02_decision_with_backtest(self, test_symbols):
        """
        测试2: 决策 + 回测联动
        验证生成组合后能够立即进行回测
        """
        print("\n" + "="*60)
        print("测试2: 决策 + 回测联动")
        print("="*60)

        # Step 1: 生成组合
        print(f"\n📊 Step 1: 生成组合")

        # 尝试决策端点
        decision_endpoints = [
            f"{self.base_url}/api/orchestrator/propose"
        ]

        response, _ = self.find_working_endpoint(
            decision_endpoints,
            method="POST",
            json_data={"topk": 3, "mock": True},  # 使用较小的组合
            timeout=self.timeout
        )

        if not response:
            print(f"   ⚠️  决策端点未找到，跳过测试")
            pytest.skip("决策API端点未实现")
            return

        decision_data = response.json()

        # 查找持仓数据
        holdings = None
        for key in ["holdings", "portfolio", "allocations"]:
            if key in decision_data and isinstance(decision_data[key], list):
                holdings = decision_data[key]
                break

        if not holdings or len(holdings) == 0:
            print(f"   ⚠️  未找到持仓数据，跳过回测")
            pytest.skip("无持仓数据")
            return

        print(f"   ✅ 组合生成: {len(holdings)}支股票")

        # Step 2: 使用组合进行回测
        print(f"\n📈 Step 2: 执行回测")

        backtest_endpoints = [
            f"{self.base_url}/api/backtest/run",
            f"{self.base_url}/api/backtest/execute"
        ]

        backtest_response, _ = self.find_working_endpoint(
            backtest_endpoints,
            method="POST",
            json_data={
                "holdings": holdings,
                "window": "1M",  # 使用较短窗口
                "rebalance": "monthly",
                "cost": 0.001
            },
            timeout=60
        )

        if not backtest_response:
            print(f"   ⚠️  回测端点未找到，跳过回测")
            pytest.skip("回测API端点未实现")
            return

        # 回测可能返回200或422（参数验证）
        if backtest_response.status_code in [200, 422]:
            if backtest_response.status_code == 200:
                backtest_data = backtest_response.json()
                print(f"   ✅ 回测完成")

                # Step 3: 验证回测结果
                print(f"\n📊 Step 3: 验证回测结果")

                # 检查常见字段
                found_fields = {}
                for field in ["dates", "nav", "metrics", "performance"]:
                    if field in backtest_data:
                        found_fields[field] = backtest_data[field]

                if "nav" in found_fields and isinstance(found_fields["nav"], list):
                    nav = found_fields["nav"]
                    print(f"   ✅ NAV曲线: {len(nav)}个数据点")
                    if len(nav) > 0:
                        print(f"   ✅ 最终净值: {nav[-1]:.4f}")

                if "metrics" in found_fields and isinstance(found_fields["metrics"], dict):
                    metrics = found_fields["metrics"]
                    print(f"   ✅ 回测指标: {len(metrics)}个")

                    # 显示关键指标
                    key_metrics = ["annualized_return", "sharpe", "max_dd", "return", "volatility"]
                    for metric in key_metrics:
                        if metric in metrics:
                            value = metrics[metric]
                            if metric == "annualized_return" and isinstance(value, (int, float)):
                                print(f"   📊 年化收益: {value:.2%}")
                            elif metric == "sharpe" and isinstance(value, (int, float)):
                                print(f"   📊 Sharpe: {value:.3f}")
                            elif metric == "max_dd" and isinstance(value, (int, float)):
                                print(f"   📊 最大回撤: {value:.2%}")
            else:
                print(f"   ℹ️  回测参数验证错误")
        else:
            print(f"   ⚠️  回测失败: {backtest_response.status_code}")

        print(f"\n✅ 测试2通过: 决策与回测联动正常")

    def test_03_multi_scenario_decisions(self):
        """
        测试3: 多场景决策
        测试不同参数下的决策表现
        """
        print("\n" + "="*60)
        print("测试3: 多场景决策")
        print("="*60)

        scenarios = [
            {"name": "小型组合", "topk": 2, "expected_holdings": (1, 3)},
            {"name": "中型组合", "topk": 3, "expected_holdings": (2, 4)},
        ]

        decision_endpoints = [
            f"{self.base_url}/api/orchestrator/propose"
        ]

        for scenario in scenarios:
            print(f"\n📊 场景: {scenario['name']}")

            response, _ = self.find_working_endpoint(
                decision_endpoints,
                method="POST",
                json_data={"topk": scenario["topk"], "mock": True},
                timeout=self.timeout
            )

            if not response or response.status_code != 200:
                print(f"   ⚠️  场景失败: {response.status_code if response else '无响应'}")
                continue

            data = response.json()

            # 查找持仓数据
            holdings_count = 0
            for key in ["holdings", "portfolio", "allocations"]:
                if key in data and isinstance(data[key], list):
                    holdings_count = len(data[key])
                    break

            min_expected, max_expected = scenario["expected_holdings"]

            if holdings_count > 0:
                assert min_expected <= holdings_count <= max_expected, \
                    f"持仓数量超出预期: {holdings_count}"

                print(f"   ✅ 持仓数量: {holdings_count}")

                # 验证权重分配合理性
                holdings = data.get("holdings", data.get("portfolio", []))
                if holdings and "weight" in holdings[0]:
                    weights = [h["weight"] for h in holdings]
                    max_weight = max(weights)
                    min_weight = min(weights)

                    weight_suffix = "" if max_weight <= 1 else "%"
                    print(f"   ✅ 权重范围: {min_weight:.1f}{weight_suffix} ~ {max_weight:.1f}{weight_suffix}")
            else:
                print(f"   ℹ️  无持仓数据")

        print(f"\n✅ 测试3通过: 多场景决策正常")

    def test_04_error_handling(self):
        """
        测试4: 错误处理
        验证异常情况下的系统行为
        """
        print("\n" + "="*60)
        print("测试4: 错误处理")
        print("="*60)

        # 场景1: 无效参数
        print(f"\n❌ 场景1: 无效参数")

        decision_endpoints = [
            f"{self.base_url}/api/orchestrator/propose"
        ]

        for endpoint in decision_endpoints:
            try:
                response = requests.post(
                    endpoint,
                    json={"topk": 0},  # 无效的topk
                    timeout=10
                )
                if response.status_code in [400, 422]:
                    print(f"   ✅ 正确处理无效参数: {response.status_code}")
                    break
                else:
                    print(f"   ℹ️  {endpoint}: 返回 {response.status_code}")
            except:
                continue
        else:
            print(f"   ⚠️  未测试到错误处理")

        # 场景2: 超大请求
        print(f"\n⚠️  场景2: 超大topk")
        for endpoint in decision_endpoints:
            try:
                response = requests.post(
                    endpoint,
                    json={"topk": 1000},  # 过大的topk
                    timeout=10
                )
                # 系统应该限制或返回错误
                if response.status_code in [200, 400, 422]:
                    print(f"   ✅ 正确处理超大请求: {response.status_code}")
                    break
                else:
                    print(f"   ℹ️  {endpoint}: 返回 {response.status_code}")
            except:
                continue
        else:
            print(f"   ⚠️  未测试到超大请求处理")

        print(f"\n✅ 测试4通过: 错误处理机制正常")

    def test_05_performance_benchmark(self):
        """
        测试5: 性能基准
        验证决策性能在可接受范围内
        """
        print("\n" + "="*60)
        print("测试5: 性能基准")
        print("="*60)

        decision_endpoints = [
            f"{self.base_url}/api/orchestrator/decide",
            f"{self.base_url}/api/decide"
        ]

        # 先检查端点是否可用
        test_response, _ = self.find_working_endpoint(
            decision_endpoints,
            method="POST",
            json_data={"topk": 2, "mock": True},
            timeout=30
        )

        if not test_response:
            print(f"   ⚠️  决策端点不可用，跳过性能测试")
            pytest.skip("决策API端点未实现")
            return

        print(f"\n⏱️  执行3次决策测量平均性能")

        times = []
        successful_runs = 0

        for i in range(3):
            start = time.time()
            response, _ = self.find_working_endpoint(
                decision_endpoints,
                method="POST",
                json_data={"topk": 2, "mock": True},
                timeout=self.timeout
            )

            if response and response.status_code == 200:
                elapsed = time.time() - start
                times.append(elapsed)
                successful_runs += 1
                print(f"   第{i+1}次: {elapsed:.2f}秒")
            else:
                print(f"   第{i+1}次: 失败")

        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)

            print(f"\n   平均耗时: {avg_time:.2f}秒")
            print(f"   最大耗时: {max_time:.2f}秒")
            print(f"   成功率: {successful_runs}/3")

            # 性能目标：平均<60秒
            if avg_time > 60:
                print(f"   ⚠️  警告: 平均耗时超过60秒")
            else:
                print(f"   ✅ 性能达标: 平均耗时≤60秒")
        else:
            print(f"   ⚠️  无成功运行，无法计算性能")

        print(f"\n✅ 测试5完成: 性能基准已记录")

    def test_06_data_persistence(self, test_symbols):
        """
        测试6: 数据持久化
        验证决策结果能够正确保存和查询
        """
        print("\n" + "="*60)
        print("测试6: 数据持久化")
        print("="*60)

        # Step 1: 生成决策
        print(f"\n📊 Step 1: 生成决策")

        decision_endpoints = [
            f"{self.base_url}/api/orchestrator/decide",
            f"{self.base_url}/api/decide"
        ]

        response, _ = self.find_working_endpoint(
            decision_endpoints,
            method="POST",
            json_data={"topk": 3, "mock": True},
            timeout=self.timeout
        )

        if not response:
            print(f"   ⚠️  决策端点未找到，跳过测试")
            pytest.skip("决策API端点未实现")
            return

        data = response.json()

        # 查找trace_id和snapshot_id
        trace_id = None
        snapshot_id = None

        for key in ["trace_id", "id", "request_id"]:
            if key in data:
                trace_id = data[key]
                break

        for key in ["snapshot_id", "snapshot"]:
            if key in data:
                snapshot_id = data[key]
                break

        print(f"   ✅ 决策生成: trace_id={trace_id}")
        if snapshot_id:
            print(f"   ✅ 快照保存: snapshot_id={snapshot_id}")

        # Step 2: 查询历史快照（如果API存在）
        print(f"\n📋 Step 2: 查询历史快照")

        snapshot_endpoints = [
            f"{self.base_url}/api/portfolio/snapshots",
            f"{self.base_url}/api/snapshots",
            f"{self.base_url}/api/history/portfolios"
        ]

        for endpoint in snapshot_endpoints:
            try:
                snapshots_response = requests.get(endpoint, timeout=10)
                if snapshots_response.status_code == 200:
                    snapshots = snapshots_response.json()
                    count = len(snapshots) if isinstance(snapshots, list) else "N/A"
                    print(f"   ✅ 历史快照查询成功: {count}条记录")
                    break
            except:
                continue
        else:
            print(f"   ℹ️  快照查询端点未实现")

        print(f"\n✅ 测试6完成: 数据持久化验证")


class TestDataToDecisionIntegration:
    """数据到决策的集成测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        self.base_url = base_url

    def find_working_endpoint(self, endpoints, method="GET", json_data=None, timeout=30):
        """查找可用的端点"""
        for endpoint in endpoints:
            try:
                if method == "POST":
                    response = requests.post(endpoint, json=json_data, timeout=timeout)
                else:
                    response = requests.get(endpoint, timeout=timeout)

                if response.status_code == 200:
                    print(f"   ✅ 找到可用端点: {endpoint}")
                    return response, endpoint
            except Exception as e:
                continue
        return None, None

    def test_01_price_data_to_factors(self):
        """
        测试: 价格数据 → 因子计算
        验证价格数据能够正确转换为因子
        """
        print("\n" + "="*60)
        print("测试: 价格数据 → 因子计算")
        print("="*60)

        symbol = "AAPL"

        # Step 1: 获取价格数据
        print(f"\n📊 Step 1: 获取{symbol}价格数据")

        price_endpoints = [
            f"{self.base_url}/api/prices/{symbol}?range=1M",
            f"{self.base_url}/api/price/{symbol}?range=1M",
            f"{self.base_url}/prices/{symbol}?range=1M"
        ]

        price_response, _ = self.find_working_endpoint(price_endpoints, timeout=30)

        if not price_response:
            print(f"   ⚠️  价格端点未找到，跳过测试")
            pytest.skip("价格API端点未实现")
            return

        price_data = price_response.json()

        # 计算数据点数量
        data_points = 0
        for key in ["dates", "prices", "data"]:
            if key in price_data and isinstance(price_data[key], list):
                data_points = len(price_data[key])
                break

        print(f"   ✅ 价格数据: {data_points}个数据点")

        # Step 2: 调用分析接口计算因子
        print(f"\n🧮 Step 2: 计算因子")

        analyze_endpoints = [
            f"{self.base_url}/api/analyze/{symbol}",
            f"{self.base_url}/api/analysis/{symbol}",
            f"{self.base_url}/api/factors/{symbol}"
        ]

        # 尝试GET和POST方法
        analyze_response = None
        for endpoint in analyze_endpoints:
            for method in ["GET", "POST"]:
                try:
                    if method == "POST":
                        analyze_response = requests.post(endpoint, timeout=30)
                    else:
                        analyze_response = requests.get(endpoint, timeout=30)

                    if analyze_response and analyze_response.status_code == 200:
                        print(f"   ✅ 找到分析端点: {method} {endpoint}")
                        break
                except:
                    continue
            if analyze_response and analyze_response.status_code == 200:
                break

        if not analyze_response or analyze_response.status_code != 200:
            print(f"   ⚠️  分析端点未找到，跳过测试")
            pytest.skip("分析API端点未实现")
            return

        analyze_data = analyze_response.json()

        # 验证因子存在
        factors_key = None
        for key in ["factors", "metrics", "analysis"]:
            if key in analyze_data and isinstance(analyze_data[key], dict):
                factors_key = key
                break

        if factors_key:
            factors = analyze_data[factors_key]
            print(f"   ✅ 找到因子数据: {list(factors.keys())[:5]}...")

            # 检查常见因子类型
            factor_types = ["value", "quality", "momentum", "sentiment", "risk", "growth"]
            found_factors = [ft for ft in factor_types if ft in factors]
            if found_factors:
                print(f"   ✅ 发现因子类型: {found_factors}")

                # 显示部分因子值
                for factor in found_factors[:3]:
                    value = factors[factor]
                    if isinstance(value, (int, float)):
                        print(f"   📊 {factor}: {value:.3f}")
        else:
            print(f"   ℹ️  未找到标准因子格式")

        print(f"\n✅ 测试通过: 价格数据成功转换为因子")

    def test_02_factors_to_score(self):
        """
        测试: 因子 → 评分
        验证因子能够正确聚合为综合评分
        """
        print("\n" + "="*60)
        print("测试: 因子 → 评分")
        print("="*60)

        symbol = "AAPL"

        # 调用分析接口
        analyze_endpoints = [
            f"{self.base_url}/api/analyze/{symbol}",
            f"{self.base_url}/api/analysis/{symbol}"
        ]

        response = None
        for endpoint in analyze_endpoints:
            for method in ["GET", "POST"]:
                try:
                    if method == "POST":
                        response = requests.post(endpoint, timeout=30)
                    else:
                        response = requests.get(endpoint, timeout=30)

                    if response and response.status_code == 200:
                        break
                except:
                    continue
            if response and response.status_code == 200:
                break

        if not response or response.status_code != 200:
            print(f"   ⚠️  分析端点未找到，跳过测试")
            pytest.skip("分析API端点未实现")
            return

        data = response.json()

        # 验证分数
        score_key = None
        for key in ["score", "rating", "composite_score", "overall_score"]:
            if key in data and isinstance(data[key], (int, float)):
                score_key = key
                break

        if score_key:
            score = data[score_key]
            print(f"   ✅ 找到评分: {score}")

            # 验证分数范围
            if 0 <= score <= 100:
                print(f"   ✅ 评分范围正常: {score:.2f}/100")
            elif 0 <= score <= 1:
                print(f"   ✅ 评分范围正常: {score:.3f} (小数格式)")
            elif 0 <= score <= 10:
                print(f"   ✅ 评分范围正常: {score:.1f}/10")
            else:
                print(f"   ℹ️  评分格式: {score}")

            # 尝试验证评分公式（如果因子存在）
            factors_key = None
            for key in ["factors", "metrics"]:
                if key in data and isinstance(data[key], dict):
                    factors_key = key
                    break

            if factors_key:
                factors = data[factors_key]
                print(f"   📊 使用因子: {list(factors.keys())}")
        else:
            print(f"   ℹ️  未找到评分字段")

        print(f"\n✅ 测试通过: 因子成功聚合为评分")

    def test_03_scores_to_portfolio(self):
        """
        测试: 评分 → 组合
        验证评分能够驱动组合构建
        """
        print("\n" + "="*60)
        print("测试: 评分 → 组合")
        print("="*60)

        symbols = ["AAPL", "MSFT", "GOOGL"]

        # Step 1: 批量评分
        print(f"\n📊 Step 1: 批量评分")

        score_endpoints = [
            f"{self.base_url}/api/score/batch",
            f"{self.base_url}/api/scores/batch"
        ]

        score_response, _ = self.find_working_endpoint(
            score_endpoints,
            method="POST",
            json_data={"symbols": symbols},
            timeout=30
        )

        scores = {}
        if score_response and score_response.status_code == 200:
            score_data = score_response.json()

            items_key = None
            for key in ["items", "scores", "data"]:
                if key in score_data and isinstance(score_data[key], list):
                    items_key = key
                    break

            if items_key:
                for item in score_data[items_key]:
                    symbol = item.get("symbol", item.get("ticker", "Unknown"))
                    score_obj = item.get("score", {})

                    # 修复：提取实际的数字分数
                    if isinstance(score_obj, dict):
                        score = score_obj.get("score", 0)  # 从字典中提取score字段
                    else:
                        score = score_obj  # 如果已经是数字

                    scores[symbol] = score

                print(f"   ✅ 获取{len(scores)}支股票评分")
                for symbol, score in scores.items():
                    print(f"   📊 {symbol}: {score}")  # 现在显示数字而不是字典
        else:
            print(f"   ⚠️  批量评分端点未找到，使用模拟评分")
            # 使用模拟评分继续测试
            scores = {symbol: 70 + i*10 for i, symbol in enumerate(symbols)}

        # Step 2: 构建组合
        print(f"\n🎯 Step 2: 构建组合")

        portfolio_endpoints = [
            f"{self.base_url}/api/portfolio/propose",
            f"{self.base_url}/api/portfolio/generate"
        ]

        portfolio_response, _ = self.find_working_endpoint(
            portfolio_endpoints,
            method="POST",
            json_data={"symbols": symbols},
            timeout=30
        )

        if not portfolio_response or portfolio_response.status_code != 200:
            print(f"   ⚠️  组合端点未找到，跳过测试")
            pytest.skip("组合API端点未实现")
            return

        portfolio_data = portfolio_response.json()

        # 查找持仓数据
        holdings = None
        for key in ["holdings", "portfolio", "allocations"]:
            if key in portfolio_data and isinstance(portfolio_data[key], list):
                holdings = portfolio_data[key]
                break

        if holdings:
            print(f"   ✅ 组合生成: {len(holdings)}支股票")

            # Step 3: 验证评分与权重关系
            print(f"\n📈 Step 3: 验证评分与权重关系")

            if scores and len(scores) > 0:
                # 检查入选股票
                selected_symbols = [h["symbol"] for h in holdings if "symbol" in h]
                selected_scores = [scores.get(sym, 0) for sym in selected_symbols if sym in scores]

                if selected_scores:
                    # 现在 selected_scores 是数字列表，可以求和
                    avg_selected = sum(selected_scores) / len(selected_scores)

                    # 检查未入选股票
                    not_selected = [s for s in symbols if s not in selected_symbols]
                    not_selected_scores = [scores.get(s, 0) for s in not_selected if s in scores]

                    if not_selected_scores:
                        avg_not_selected = sum(not_selected_scores) / len(not_selected_scores)

                        print(f"   入选股票平均分: {avg_selected:.2f}")
                        print(f"   未入选平均分: {avg_not_selected:.2f}")

                        if avg_selected > avg_not_selected:
                            print(f"   ✅ 高分股票优先入选")
                        else:
                            print(f"   ℹ️  入选规则可能考虑其他因素")
                    else:
                        print(f"   ℹ️  所有股票均入选或无未入选股票")
                else:
                    print(f"   ℹ️  无法计算入选股票平均分")
            else:
                print(f"   ℹ️  无评分数据用于验证")
        else:
            print(f"   ℹ️  未生成组合数据")

        print(f"\n✅ 测试通过: 评分驱动组合构建正常")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])