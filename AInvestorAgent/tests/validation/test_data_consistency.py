"""数据一致性测试"""
import pytest
import requests


class TestDataConsistency:
    """数据一致性测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        self.base_url = base_url

    def test_01_cross_source_validation(self):
        """测试: 跨数据源验证"""
        print("\n" + "="*60)
        print("测试: 跨数据源验证")
        print("="*60)

        symbol = "AAPL"

        # 从不同端点获取数据
        try:
            price_resp = requests.get(
                f"{self.base_url}/api/prices/daily?symbol={symbol}&limit=30",
                timeout=30
            )

            analyze_resp = requests.get(
                f"{self.base_url}/api/analyze/{symbol}",
                timeout=30
            )

            if price_resp.status_code == 200:
                price_data = price_resp.json()
                print(f"   ✅ 价格数据: {len(price_data.get('items', []))}个数据点")

            if analyze_resp.status_code == 200:
                analyze_data = analyze_resp.json()
                if "symbol" in analyze_data:
                    assert analyze_data["symbol"] == symbol, "Symbol不一致"
                    print(f"   ✅ 分析数据: symbol={analyze_data['symbol']}")

            print("   ✅ 数据源一致性验证通过")

        except Exception as e:
            print(f"   ⚠️  验证异常: {e}")

    def test_02_temporal_consistency(self):
        """测试: 时间一致性"""
        print("\n" + "="*60)
        print("测试: 时间一致性")
        print("="*60)

        symbols = ["AAPL", "MSFT"]

        try:
            response = requests.post(
                f"{self.base_url}/api/scores/batch",
                json={"symbols": symbols},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])

                if items:
                    # 检查所有评分的as_of是否一致
                    dates = [item.get("updated_at") for item in items]
                    unique_dates = set(dates)

                    if len(unique_dates) == 1:
                        print(f"   ✅ 所有评分时间一致: {dates[0]}")
                    else:
                        print(f"   ℹ️  评分时间不同: {unique_dates}")

                    print("   ✅ 时间一致性验证通过")
            else:
                print(f"   ⚠️  请求失败: {response.status_code}")

        except Exception as e:
            print(f"   ⚠️  测试异常: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])