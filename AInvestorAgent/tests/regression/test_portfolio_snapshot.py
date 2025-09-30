"""组合快照测试 - 验证组合快照的一致性和可恢复性"""
import pytest
import requests
from datetime import datetime


class TestPortfolioSnapshot:
    """组合快照测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        self.base_url = base_url

    def test_01_snapshot_creation(self):
        """测试: 快照创建"""
        print("\n" + "="*60)
        print("测试: 快照创建")
        print("="*60)

        candidates = [
            {"symbol": "AAPL", "sector": "Technology", "score": 80.0},
            {"symbol": "MSFT", "sector": "Technology", "score": 75.0}
        ]

        response = requests.post(
            f"{self.base_url}/api/orchestrator/propose",
            json={"candidates": candidates, "params": {"mock": True}},
            timeout=30
        )

        if response.status_code != 200:
            print(f"   ℹ️  组合API不可用: {response.status_code}")
            pytest.skip("组合API不可用")
            return

        data = response.json()
        context = data.get("context", {})
        kept = context.get("kept", [])

        assert len(kept) > 0, "快照应包含持仓"
        print(f"   ✅ 快照创建成功: {len(kept)}支股票")

    def test_02_snapshot_consistency(self):
        """测试: 快照一致性"""
        print("\n" + "="*60)
        print("测试: 快照一致性")
        print("="*60)

        candidates = [
            {"symbol": "AAPL", "sector": "Technology", "score": 80.0},
            {"symbol": "MSFT", "sector": "Technology", "score": 75.0},
            {"symbol": "GOOGL", "sector": "Technology", "score": 70.0}
        ]

        # 连续创建两次相同的快照
        results = []
        for i in range(2):
            response = requests.post(
                f"{self.base_url}/api/orchestrator/propose",
                json={"candidates": candidates, "params": {"mock": True}},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                context = data.get("context", {})
                kept = context.get("kept", [])
                results.append(kept)

        if len(results) == 2:
            # 验证两次结果的持仓数量一致
            assert len(results[0]) == len(results[1]), \
                f"两次快照持仓数不同: {len(results[0])} vs {len(results[1])}"

            # 验证股票列表一致
            symbols1 = sorted([h["symbol"] for h in results[0]])
            symbols2 = sorted([h["symbol"] for h in results[1]])
            assert symbols1 == symbols2, "两次快照股票列表不同"

            print(f"   ✅ 快照一致性验证通过")
        else:
            print(f"   ℹ️  未能获取足够的快照数据")

    def test_03_snapshot_weight_sum(self):
        """测试: 快照权重总和"""
        print("\n" + "="*60)
        print("测试: 快照权重总和")
        print("="*60)

        candidates = [
            {"symbol": "AAPL", "sector": "Technology", "score": 80.0},
            {"symbol": "MSFT", "sector": "Technology", "score": 75.0}
        ]

        response = requests.post(
            f"{self.base_url}/api/orchestrator/propose",
            json={"candidates": candidates, "params": {"mock": True}},
            timeout=30
        )

        if response.status_code != 200:
            pytest.skip("组合API不可用")
            return

        data = response.json()
        context = data.get("context", {})
        kept = context.get("kept", [])

        if kept:
            total_weight = sum(h.get("weight", 0) for h in kept)

            # 判断权重格式（小数或百分比）
            if total_weight <= 1.5:
                assert 0.95 <= total_weight <= 1.05, \
                    f"权重总和异常: {total_weight}"
                print(f"   ✅ 权重总和: {total_weight:.3f} (小数格式)")
            else:
                assert 99 <= total_weight <= 101, \
                    f"权重总和异常: {total_weight}"
                print(f"   ✅ 权重总和: {total_weight:.1f}% (百分比格式)")
        else:
            print(f"   ℹ️  无持仓数据")

    def test_04_snapshot_with_constraints(self):
        """测试: 带约束的快照"""
        print("\n" + "="*60)
        print("测试: 带约束的快照")
        print("="*60)

        candidates = [
            {"symbol": "AAPL", "sector": "Technology", "score": 90.0},
            {"symbol": "MSFT", "sector": "Technology", "score": 85.0},
            {"symbol": "GOOGL", "sector": "Technology", "score": 80.0},
            {"symbol": "NVDA", "sector": "Technology", "score": 75.0}
        ]

        response = requests.post(
            f"{self.base_url}/api/orchestrator/propose",
            json={
                "candidates": candidates,
                "params": {
                    "mock": True,
                    "risk.max_stock": 0.30,
                    "risk.max_sector": 0.50
                }
            },
            timeout=30
        )

        if response.status_code != 200:
            pytest.skip("组合API不可用")
            return

        data = response.json()
        context = data.get("context", {})
        kept = context.get("kept", [])

        if kept:
            # 验证单票权重约束
            max_weight = max(h.get("weight", 0) for h in kept)
            if max_weight <= 1:
                assert max_weight <= 0.35, f"单票权重超限: {max_weight}"
            else:
                assert max_weight <= 35, f"单票权重超限: {max_weight}%"

            print(f"   ✅ 约束验证通过")
            print(f"   📊 最大单票权重: {max_weight:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])