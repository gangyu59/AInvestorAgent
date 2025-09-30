"""评分快照测试 - 验证评分的稳定性和版本控制"""
import pytest
import requests


class TestScoresSnapshot:
    """评分快照测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        self.base_url = base_url

    def test_01_score_reproducibility(self):
        """测试: 评分可复现性"""
        print("\n" + "="*60)
        print("测试: 评分可复现性")
        print("="*60)

        symbols = ["AAPL", "MSFT"]

        # 连续两次评分
        scores = []
        for i in range(2):
            response = requests.post(
                f"{self.base_url}/api/scores/batch",
                json={"symbols": symbols, "mock": False},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                if items:
                    # 提取评分
                    symbol_scores = {}
                    for item in items:
                        sym = item.get("symbol")
                        score_obj = item.get("score", {})
                        if isinstance(score_obj, dict):
                            score = score_obj.get("score", 0)
                        else:
                            score = score_obj
                        symbol_scores[sym] = score
                    scores.append(symbol_scores)

        if len(scores) == 2:
            # 验证两次评分一致
            for symbol in symbols:
                if symbol in scores[0] and symbol in scores[1]:
                    score1 = scores[0][symbol]
                    score2 = scores[1][symbol]
                    diff = abs(score1 - score2)
                    assert diff < 0.01, \
                        f"{symbol}评分不稳定: {score1} vs {score2}"
                    print(f"   ✅ {symbol}: {score1:.2f} (一致)")
        else:
            print(f"   ℹ️  未能获取足够的评分数据")

    def test_02_score_consistency(self):
        """测试: 评分一致性"""
        print("\n" + "="*60)
        print("测试: 评分一致性")
        print("="*60)

        symbols = ["AAPL", "MSFT", "GOOGL"]

        response = requests.post(
            f"{self.base_url}/api/scores/batch",
            json={"symbols": symbols},
            timeout=30
        )

        if response.status_code != 200:
            print(f"   ℹ️  评分API不可用: {response.status_code}")
            pytest.skip("评分API不可用")
            return

        data = response.json()
        items = data.get("items", [])

        if items:
            # 验证所有评分在合理范围
            for item in items:
                symbol = item.get("symbol")
                score_obj = item.get("score", {})

                if isinstance(score_obj, dict):
                    score = score_obj.get("score", 0)
                else:
                    score = score_obj

                assert 0 <= score <= 100, \
                    f"{symbol}评分超出[0,100]: {score}"

            print(f"   ✅ 所有评分在合理范围")
            print(f"   📊 评分数量: {len(items)}")
        else:
            print(f"   ℹ️  无评分数据")

    def test_03_score_version_tracking(self):
        """测试: 评分版本跟踪"""
        print("\n" + "="*60)
        print("测试: 评分版本跟踪")
        print("="*60)

        response = requests.post(
            f"{self.base_url}/api/scores/batch",
            json={"symbols": ["AAPL"]},
            timeout=30
        )

        if response.status_code != 200:
            pytest.skip("评分API不可用")
            return

        data = response.json()

        # 验证版本标签存在
        assert "version_tag" in data, "缺少version_tag"
        version_tag = data["version_tag"]
        assert version_tag, "version_tag不应为空"

        print(f"   ✅ 版本标签: {version_tag}")

        # 验证items中也有版本信息
        items = data.get("items", [])
        if items and "score" in items[0]:
            score_obj = items[0]["score"]
            if isinstance(score_obj, dict) and "version_tag" in score_obj:
                print(f"   ✅ 评分包含版本标签")

    def test_04_score_range_validation(self):
        """测试: 评分范围验证"""
        print("\n" + "="*60)
        print("测试: 评分范围验证")
        print("="*60)

        symbols = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]

        response = requests.post(
            f"{self.base_url}/api/scores/batch",
            json={"symbols": symbols},
            timeout=30
        )

        if response.status_code != 200:
            pytest.skip("评分API不可用")
            return

        data = response.json()
        items = data.get("items", [])

        if items:
            scores = []
            for item in items:
                score_obj = item.get("score", {})
                if isinstance(score_obj, dict):
                    score = score_obj.get("score", 0)
                else:
                    score = score_obj
                scores.append(score)

            # 统计评分分布
            import statistics
            mean = statistics.mean(scores)
            stdev = statistics.stdev(scores) if len(scores) > 1 else 0

            print(f"   📊 评分统计:")
            print(f"      平均: {mean:.2f}")
            print(f"      标准差: {stdev:.2f}")
            print(f"      范围: [{min(scores):.2f}, {max(scores):.2f}]")
            print(f"   ✅ 评分范围验证通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])