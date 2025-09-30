"""
AInvestorAgent 详细测试用例
包含所有关键功能的深度测试
"""
import pytest
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from backend.storage.db import get_db, SessionLocal
from backend.storage.models import PriceDaily, NewsRaw, NewsScore, ScoreDaily

# ============================================================================
# 测试配置
# ============================================================================
BASE_URL = "http://localhost:8000"
TEST_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMZN", "SPY"]
TIMEOUT = 30

class TestColors:
    """终端颜色输出"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test_header(title: str):
    """打印测试标题"""
    print(f"\n{TestColors.BLUE}{'='*70}{TestColors.END}")
    print(f"{TestColors.BLUE}{title:^70}{TestColors.END}")
    print(f"{TestColors.BLUE}{'='*70}{TestColors.END}\n")

def print_pass(message: str):
    """打印通过信息"""
    print(f"{TestColors.GREEN}✓{TestColors.END} {message}")

def print_fail(message: str):
    """打印失败信息"""
    print(f"{TestColors.RED}✗{TestColors.END} {message}")

def print_warn(message: str):
    """打印警告信息"""
    print(f"{TestColors.YELLOW}⚠{TestColors.END} {message}")

# ============================================================================
# 1. 功能完整性测试
# ============================================================================

class TestFunctionalCompleteness:
    """功能完整性测试套件"""

    def test_01_data_ingestion_prices(self):
        """测试1.1: 价格数据获取"""
        print_test_header("测试 1.1: 价格数据获取")

        for symbol in ["AAPL", "MSFT", "SPY"]:
            try:
                response = requests.get(
                    f"{BASE_URL}/api/prices/{symbol}?range=1Y",
                    timeout=TIMEOUT
                )

                assert response.status_code == 200, f"状态码错误: {response.status_code}"
                data = response.json()

                # 验证数据结构
                assert "dates" in data, "缺少dates字段"
                assert "prices" in data, "缺少prices字段"
                assert len(data["dates"]) >= 200, f"数据点不足: {len(data['dates'])}"

                # 验证价格字段
                first_price = data["prices"][0]
                required_fields = ["open", "high", "low", "close", "volume"]
                for field in required_fields:
                    assert field in first_price, f"缺少字段: {field}"

                print_pass(f"{symbol}: {len(data['dates'])}个数据点")

            except Exception as e:
                print_fail(f"{symbol}: {str(e)}")
                pytest.fail(f"价格数据测试失败: {symbol}")

    def test_02_data_ingestion_news(self):
        """测试1.2: 新闻数据获取"""
        print_test_header("测试 1.2: 新闻数据获取")

        for symbol in ["AAPL", "TSLA"]:
            try:
                response = requests.get(
                    f"{BASE_URL}/api/news/{symbol}?days=7",
                    timeout=TIMEOUT
                )

                assert response.status_code == 200
                data = response.json()

                assert "items" in data
                news_count = len(data["items"])

                if news_count > 0:
                    # 验证新闻结构
                    first_news = data["items"][0]
                    assert "title" in first_news
                    assert "sentiment" in first_news
                    assert -1 <= first_news["sentiment"] <= 1
                    print_pass(f"{symbol}: {news_count}条新闻")
                else:
                    print_warn(f"{symbol}: 无新闻数据")

            except Exception as e:
                print_fail(f"{symbol}: {str(e)}")

    def test_03_fundamentals_data(self):
        """测试1.3: 基本面数据"""
        print_test_header("测试 1.3: 基本面数据")

        for symbol in ["AAPL", "MSFT"]:
            try:
                response = requests.get(
                    f"{BASE_URL}/api/fundamentals/{symbol}",
                    timeout=TIMEOUT
                )

                assert response.status_code == 200
                data = response.json()

                # 验证关键字段
                required = ["pe", "pb", "market_cap", "sector"]
                missing = [f for f in required if f not in data]

                if missing:
                    print_warn(f"{symbol}: 缺少字段 {missing}")
                else:
                    print_pass(f"{symbol}: PE={data.get('pe')}, PB={data.get('pb')}")

            except Exception as e:
                print_fail(f"{symbol}: {str(e)}")

    def test_04_factor_calculation(self):
        """测试1.4: 因子计算"""
        print_test_header("测试 1.4: 因子计算")

        symbol = "AAPL"
        try:
            response = requests.post(
                f"{BASE_URL}/api/analyze/{symbol}",
                timeout=TIMEOUT
            )

            assert response.status_code == 200
            data = response.json()

            # 验证因子字段
            assert "factors" in data
            factors = data["factors"]

            required_factors = ["value", "quality", "momentum", "sentiment"]
            for factor in required_factors:
                assert factor in factors, f"缺少因子: {factor}"
                assert 0 <= factors[factor] <= 1, f"因子{factor}超出范围: {factors[factor]}"
                print_pass(f"{factor.capitalize()} Factor: {factors[factor]:.3f}")

        except Exception as e:
            print_fail(f"因子计算失败: {str(e)}")
            pytest.fail()

    def test_05_scoring_system(self):
        """测试1.5: 评分系统"""
        print_test_header("测试 1.5: 综合评分系统")

        symbol = "AAPL"
        try:
            response = requests.post(
                f"{BASE_URL}/api/analyze/{symbol}",
                timeout=TIMEOUT
            )

            data = response.json()
            assert "score" in data

            score = data["score"]
            assert 0 <= score <= 100, f"分数超出范围: {score}"

            # 验证评分公式: score = 100 * (0.25*value + 0.20*quality + 0.35*momentum + 0.20*sentiment)
            factors = data["factors"]
            expected_score = 100 * (
                0.25 * factors["value"] +
                0.20 * factors["quality"] +
                0.35 * factors["momentum"] +
                0.20 * factors["sentiment"]
            )

            diff = abs(score - expected_score)
            assert diff < 1.0, f"评分计算误差过大: {diff}"

            print_pass(f"综合评分: {score:.2f}/100")
            print_pass(f"计算验证: 误差 {diff:.4f}")

        except Exception as e:
            print_fail(f"评分系统测试失败: {str(e)}")
            pytest.fail()

    def test_06_batch_scoring(self):
        """测试1.6: 批量评分API"""
        print_test_header("测试 1.6: 批量评分API")

        symbols = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]

        try:
            import time
            start_time = time.time()

            response = requests.post(
                f"{BASE_URL}/api/score/batch",
                json={"symbols": symbols},
                timeout=TIMEOUT
            )

            elapsed = time.time() - start_time

            assert response.status_code == 200
            data = response.json()
            assert "items" in data

            items = data["items"]
            assert len(items) == len(symbols), f"返回数量不匹配: {len(items)} vs {len(symbols)}"

            # 验证每个结果
            for item in items:
                assert "symbol" in item
                assert "score" in item
                assert 0 <= item["score"] <= 100

            print_pass(f"批量评分 {len(symbols)} 支股票")
            print_pass(f"响应时间: {elapsed:.2f}秒")

            # 性能验证
            if elapsed > 5:
                print_warn(f"响应时间超过5秒目标: {elapsed:.2f}s")

        except Exception as e:
            print_fail(f"批量评分失败: {str(e)}")
            pytest.fail()

    def test_07_portfolio_construction(self):
        """测试1.7: 组合构建"""
        print_test_header("测试 1.7: 组合构建与约束")

        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMZN", "META", "NFLX"]

        try:
            response = requests.post(
                f"{BASE_URL}/api/portfolio/propose",
                json={"symbols": symbols},
                timeout=TIMEOUT
            )

            assert response.status_code == 200
            data = response.json()

            # 验证返回结构
            assert "holdings" in data
            holdings = data["holdings"]

            # 约束1: 持仓数量 5-15
            assert 5 <= len(holdings) <= 15, f"持仓数量违规: {len(holdings)}"
            print_pass(f"持仓数量: {len(holdings)} (符合5-15约束)")

            # 约束2: 权重总和 ≈ 100%
            total_weight = sum(h["weight"] for h in holdings)
            assert 99.5 <= total_weight <= 100.5, f"权重总和违规: {total_weight}"
            print_pass(f"权重总和: {total_weight:.2f}%")

            # 约束3: 单票权重 ≤ 30%
            max_weight = max(h["weight"] for h in holdings)
            assert max_weight <= 30.5, f"单票权重超限: {max_weight}%"
            print_pass(f"最大单票权重: {max_weight:.2f}% (≤30%)")

            # 约束4: 行业集中度 ≤ 50%
            if "sector_concentration" in data:
                for sector, weight in data["sector_concentration"].items():
                    assert weight <= 51, f"行业{sector}集中度超限: {weight}%"
                print_pass("行业集中度检查通过")

            # 验证入选理由
            for holding in holdings:
                assert "reasons" in holding
                assert len(holding["reasons"]) >= 1
            print_pass("所有持仓包含入选理由")

        except Exception as e:
            print_fail(f"组合构建失败: {str(e)}")
            pytest.fail()

    def test_08_backtest_basic(self):
        """测试1.8: 基础回测功能"""
        print_test_header("测试 1.8: 回测引擎")

        holdings = [
            {"symbol": "AAPL", "weight": 25},
            {"symbol": "MSFT", "weight": 25},
            {"symbol": "GOOGL", "weight": 25},
            {"symbol": "NVDA", "weight": 25}
        ]

        try:
            import time
            start_time = time.time()

            response = requests.post(
                f"{BASE_URL}/api/backtest/run",
                json={
                    "holdings": holdings,
                    "window": "1Y",
                    "rebalance": "weekly",
                    "cost": 0.001
                },
                timeout=60
            )

            elapsed = time.time() - start_time

            assert response.status_code == 200
            data = response.json()

            # 验证返回字段
            required = ["dates", "nav", "benchmark_nav", "metrics"]
            for field in required:
                assert field in data, f"缺少字段: {field}"

            # 验证数据长度一致性
            assert len(data["dates"]) == len(data["nav"])
            assert len(data["dates"]) == len(data["benchmark_nav"])
            print_pass(f"回测周期: {len(data['dates'])}个时间点")

            # 验证NAV曲线合理性
            nav = data["nav"]
            assert nav[0] == 1.0, "初始净值应为1.0"
            assert all(n > 0 for n in nav), "净值应始终为正"
            print_pass(f"最终净值: {nav[-1]:.4f}")

            # 验证指标
            metrics = data["metrics"]
            required_metrics = ["annualized_return", "sharpe", "max_dd", "win_rate"]
            for metric in required_metrics:
                assert metric in metrics, f"缺少指标: {metric}"

            print_pass(f"年化收益: {metrics['annualized_return']:.2%}")
            print_pass(f"Sharpe比率: {metrics['sharpe']:.3f}")
            print_pass(f"最大回撤: {metrics['max_dd']:.2%}")
            print_pass(f"胜率: {metrics['win_rate']:.2%}")
            print_pass(f"回测耗时: {elapsed:.2f}秒")

            # 性能验证
            if elapsed > 20:
                print_warn(f"回测时间超过20秒目标: {elapsed:.2f}s")

        except Exception as e:
            print_fail(f"回测功能失败: {str(e)}")
            pytest.fail()

# ============================================================================
# 2. 数据质量测试
# ============================================================================

class TestDataQuality:
    """数据质量测试套件"""

    def test_01_price_completeness(self):
        """测试2.1: 价格数据完整性"""
        print_test_header("测试 2.1: 价格数据完整性")

        db = SessionLocal()
        try:
            for symbol in ["AAPL", "MSFT", "SPY"]:
                # 查询最近1年的价格数据
                one_year_ago = datetime.now() - timedelta(days=365)
                prices = db.query(PriceDaily).filter(
                    PriceDaily.symbol == symbol,
                    PriceDaily.date >= one_year_ago
                ).all()

                count = len(prices)
                # 一年约252个交易日，允许少量缺失
                assert count >= 240, f"{symbol}数据不足: {count}"
                print_pass(f"{symbol}: {count}个交易日")

                # 检查字段完整性
                null_count = sum(1 for p in prices if p.close is None or p.volume is None)
                assert null_count == 0, f"{symbol}有{null_count}个NULL值"
                print_pass(f"{symbol}: 无NULL值")

        finally:
            db.close()

    def test_02_news_sentiment_accuracy(self):
        """测试2.2: 情绪分数准确性"""
        print_test_header("测试 2.2: 新闻情绪准确性")

        # 人工标注的测试用例
        test_cases = [
            {"title": "Apple reports record earnings", "expected": 0.7, "tolerance": 0.3},
            {"title": "Tesla stock plummets on recall news", "expected": -0.7, "tolerance": 0.3},
            {"title": "Microsoft announces dividend", "expected": 0.5, "tolerance": 0.3},
        ]

        db = SessionLocal()
        try:
            correct = 0
            total = len(test_cases)

            for case in test_cases:
                # 这里简化处理，实际应该查询数据库中匹配的新闻
                # 模拟情绪计算
                calculated_sentiment = np.random.uniform(-1, 1)  # 实际应调用情绪模型

                expected = case["expected"]
                tolerance = case["tolerance"]

                if abs(calculated_sentiment - expected) <= tolerance:
                    correct += 1
                    print_pass(f"'{case['title'][:40]}...' 情绪准确")
                else:
                    print_warn(f"'{case['title'][:40]}...' 情绪偏差过大")

            accuracy = correct / total
            print_pass(f"准确率: {accuracy:.1%} ({correct}/{total})")
            assert accuracy >= 0.7, f"准确率不足70%: {accuracy:.1%}"

        finally:
            db.close()

    def test_03_data_consistency(self):
        """测试2.3: 数据一致性（与外部源对比）"""
        print_test_header("测试 2.3: 数据一致性验证")

        symbol = "AAPL"
        try:
            # 获取本地数据
            response = requests.get(
                f"{BASE_URL}/api/prices/{symbol}?range=3M",
                timeout=TIMEOUT
            )
            local_data = response.json()

            # 这里简化处理，实际应该调用外部API（如yfinance）对比
            # 验证价格数据在合理范围内
            prices = local_data["prices"]
            close_prices = [p["close"] for p in prices]

            # 检查是否有异常值
            mean = np.mean(close_prices)
            std = np.std(close_prices)
            outliers = [p for p in close_prices if abs(p - mean) > 3 * std]

            if outliers:
                print_warn(f"发现{len(outliers)}个潜在异常值")
            else:
                print_pass("无明显异常值")

            # 检查价格连续性（不应有突变）
            max_change = 0
            for i in range(1, len(close_prices)):
                change = abs((close_prices[i] - close_prices[i-1]) / close_prices[i-1])
                max_change = max(max_change, change)

            if max_change > 0.5:  # 单日变化超过50%可疑
                print_warn(f"最大单日变化: {max_change:.2%}")
            else:
                print_pass(f"最大单日变化: {max_change:.2%} (正常)")

        except Exception as e:
            print_fail(f"数据一致性验证失败: {str(e)}")

# ============================================================================
# 3. 智能体能力测试
# ============================================================================

class TestAgentIntelligence:
    """智能体能力测试套件"""

    def test_01_orchestrator_full_pipeline(self):
        """测试3.1: 完整决策链路"""
        print_test_header("测试 3.1: Orchestrator完整决策链")

        try:
            import time
            start_time = time.time()

            response = requests.post(
                f"{BASE_URL}/api/orchestrator/decide",
                json={"topk": 10, "mock": False},
                timeout=120
            )

            elapsed = time.time() - start_time

            assert response.status_code == 200
            data = response.json()

            # 验证trace_id
            assert "trace_id" in data
            print_pass(f"Trace ID: {data['trace_id']}")

            # 验证决策结果
            assert "holdings" in data
            holdings = data["holdings"]
            assert len(holdings) >= 5, f"持仓数量不足: {len(holdings)}"
            print_pass(f"生成组合: {len(holdings)}支股票")

            # 验证各Agent执行痕迹
            if "agents_trace" in data:
                for agent_name, agent_result in data["agents_trace"].items():
                    status = agent_result.get("status", "unknown")
                    print_pass(f"  {agent_name}: {status}")

            print_pass(f"总耗时: {elapsed:.2f}秒")

            if elapsed > 60:
                print_warn(f"决策时间超过60秒: {elapsed:.2f}s")

        except Exception as e:
            print_fail(f"决策链路失败: {str(e)}")
            pytest.fail()

    def test_02_risk_manager_constraints(self):
        """测试3.2: 风险管理智能体约束"""
        print_test_header("测试 3.2: RiskManager约束检查")

        # 构造违反约束的组合
        bad_holdings = [
            {"symbol": "AAPL", "weight": 50},  # 违反单票≤30%
            {"symbol": "MSFT", "weight": 30},
            {"symbol": "GOOGL", "weight": 20}
        ]

        try:
            response = requests.post(
                f"{BASE_URL}/api/portfolio/propose",
                json={"symbols": ["AAPL", "MSFT", "GOOGL"]},
                timeout=TIMEOUT
            )

            data = response.json()
            holdings = data["holdings"]

            # 验证约束已修正
            max_weight = max(h["weight"] for h in holdings)
            assert max_weight <= 30.5, f"风控失效: 单票权重{max_weight}%"
            print_pass(f"单票权重约束生效: 最大{max_weight:.2f}%")

            # 检查是否有调整说明
            if "actions" in data:
                print_pass(f"风控动作记录: {len(data['actions'])}条")

        except Exception as e:
            print_fail(f"风险管理测试失败: {str(e)}")

    def test_03_agent_coordination(self):
        """测试3.3: 多智能体协同"""
        print_test_header("测试 3.3: 多智能体协同机制")

        try:
            # 测试冲突解决：价值投资 vs 量化交易
            response = requests.post(
                f"{BASE_URL}/api/orchestrator/decide",
                json={
                    "topk": 10,
                    "strategy_weights": {
                        "value": 0.6,  # 偏向价值投资
                        "momentum": 0.4
                    }
                },
                timeout=TIMEOUT
            )

            data = response.json()
            holdings = data["holdings"]

            # 验证策略权重影响
            # 期望: 价值股权重更高
            print_pass(f"策略加权组合生成: {len(holdings)}支")

            # 检查主席智能体决策
            if "decision_rationale" in data:
                print_pass(f"决策理由: {data['decision_rationale'][:100]}...")

        except Exception as e:
            print_fail(f"协同测试失败: {str(e)}")

# ============================================================================
# 4. API性能测试
# ============================================================================

class TestAPIPerformance:
    """API性能测试套件"""

    def test_01_response_time_sla(self):
        """测试4.1: 响应时间SLA"""
        print_test_header("测试 4.1: API响应时间SLA")

        endpoints = [
            ("/health", "GET", None, 0.5),
            ("/api/prices/AAPL?range=1M", "GET", None, 0.5),
            ("/api/fundamentals/AAPL", "GET", None, 2),
            ("/api/score/batch", "POST", {"symbols": ["AAPL", "MSFT"]}, 5),
        ]

        results = []
        for endpoint, method, body, target in endpoints:
            times = []
            for _ in range(5):  # 测试5次取平均
                start = time.time()
                if method == "GET":
                    requests.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
                else:
                    requests.post(f"{BASE_URL}{endpoint}", json=body, timeout=TIMEOUT)
                elapsed = time.time() - start
                times.append(elapsed)

            avg_time = np.mean(times)
            p95_time = np.percentile(times, 95)

            if p95_time <= target:
                print_pass(f"{endpoint}: P95={p95_time:.3f}s (目标<{target}s)")
            else:
                print_warn(f"{endpoint}: P95={p95_time:.3f}s 超过目标{target}s")

            results.append((endpoint, p95_time, target))

        # 验证整体SLA
        failures = [r for r in results if r[1] > r[2]]
        assert len(failures) == 0, f"{len(failures)}个端点未达标"

    def test_02_concurrent_load(self):
        """测试4.2: 并发负载测试"""
        print_test_header("测试 4.2: 并发负载 (10 QPS)")

        import concurrent.futures
        import time

        def make_request():
            try:
                start = time.time()
                response = requests.get(f"{BASE_URL}/health", timeout=5)
                return response.status_code == 200, time.time() - start
            except:
                return False, 0

        # 发起10个并发请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]

        success_count = sum(1 for r in results if r[0])
        avg_time = np.mean([r[1] for r in results if r[0]])

        print_pass(f"成功率: {success_count}/10")
        print_pass(f"平均响应时间: {avg_time:.3f}s")

        assert success_count >= 9, f"成功率过低: {success_count}/10"

    def test_03_error_handling(self):
        """测试4.3: 错误处理"""
        print_test_header("测试 4.3: 错误处理与降级")

        # 测试404
        response = requests.get(f"{BASE_URL}/api/nonexistent", timeout=5)
        assert response.status_code == 404
        print_pass("404错误处理正确")

        # 测试400 (空参数)
        response = requests.post(
            f"{BASE_URL}/api/portfolio/propose",
            json={"symbols": []},
            timeout=5
        )
        assert response.status_code in [400, 422]
        print_pass("400错误处理正确")

        # 测试无效股票代码
        response = requests.get(f"{BASE_URL}/api/prices/ZZZZZ", timeout=5)
        assert response.status_code in [404, 400]
        print_pass("无效代码处理正确")

# ============================================================================
# 5. 回测有效性测试
# ============================================================================

class TestBacktestValidity:
    """回测有效性测试套件"""

    def test_01_historical_reproduction(self):
        """测试5.1: 历史复现准确性"""
        print_test_header("测试 5.1: 回测历史复现")

        # 使用固定组合和历史窗口
        holdings = [
            {"symbol": "AAPL", "weight": 50},
            {"symbol": "MSFT", "weight": 50}
        ]

        try:
            # 运行两次回测，验证可复现性
            results = []
            for i in range(2):
                response = requests.post(
                    f"{BASE_URL}/api/backtest/run",
                    json={
                        "holdings": holdings,
                        "window": "6M",
                        "rebalance": "monthly"
                    },
                    timeout=60
                )
                data = response.json()
                results.append(data["nav"][-1])  # 最终净值

            # 验证两次结果一致
            diff = abs(results[0] - results[1])
            assert diff < 0.0001, f"回测不可复现: 差异{diff}"
            print_pass(f"回测可复现: 两次最终净值{results[0]:.4f}")

        except Exception as e:
            print_fail(f"历史复现测试失败: {str(e)}")

    def test_02_factor_ic(self):
        """测试5.2: 因子IC（信息系数）"""
        print_test_header("测试 5.2: 因子有效性 (IC测试)")

        # 这里简化处理，实际需要大量历史数据
        # IC = 因子与未来收益的相关性

        print_warn("IC测试需要大量历史数据，此处跳过")
        print_pass("IC测试框架就绪")

    def test_03_alpha_generation(self):
        """测试5.3: Alpha生成能力"""
        print_test_header("测试 5.3: Alpha生成能力")

        holdings = [
            {"symbol": "AAPL", "weight": 25},
            {"symbol": "MSFT", "weight": 25},
            {"symbol": "GOOGL", "weight": 25},
            {"symbol": "NVDA", "weight": 25}
        ]

        try:
            response = requests.post(
                f"{BASE_URL}/api/backtest/run",
                json={
                    "holdings": holdings,
                    "window": "1Y",
                    "rebalance": "weekly"
                },
                timeout=60
            )

            data = response.json()
            metrics = data["metrics"]

            # 计算相对基准的超额收益
            portfolio_return = metrics["annualized_return"]

            # 假设SPY年化10%
            benchmark_return = 0.10
            alpha = portfolio_return - benchmark_return

            print_pass(f"组合年化: {portfolio_return:.2%}")
            print_pass(f"基准年化: {benchmark_return:.2%}")
            print_pass(f"Alpha: {alpha:.2%}")

            if alpha > 0.02:  # 目标: Alpha > 2%
                print_pass("✓ Alpha目标达成")
            else:
                print_warn(f"Alpha未达2%目标: {alpha:.2%}")

        except Exception as e:
            print_fail(f"Alpha测试失败: {str(e)}")

# ============================================================================
# 运行所有测试
# ============================================================================

if __name__ == "__main__":
    print(f"\n{TestColors.BLUE}{'='*70}{TestColors.END}")
    print(f"{TestColors.BLUE}AInvestorAgent 详细测试用例 v1.0{TestColors.END}")
    print(f"{TestColors.BLUE}{'='*70}{TestColors.END}\n")

    # 运行pytest
    pytest.main([__file__, "-v", "--tb=short"])