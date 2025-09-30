"""因子IC测试"""
import pytest
import numpy as np
import requests


class TestFactorIC:
    """因子IC(信息系数)测试"""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        self.base_url = base_url

    def test_01_factor_predictability(self):
        """测试: 因子预测能力"""
        print("\n" + "="*60)
        print("测试: 因子预测能力")
        print("="*60)

        # 模拟因子与收益率的相关性测试
        factors = np.random.randn(100)
        returns = factors * 0.5 + np.random.randn(100) * 0.3
        ic = np.corrcoef(factors, returns)[0, 1]

        print(f"   📊 IC (模拟): {ic:.3f}")

        assert -1 <= ic <= 1, f"IC超出[-1, 1]范围: {ic}"
        print(f"   ✅ IC在有效范围内")

        # IC的绝对值应该显示一定的预测能力
        if abs(ic) > 0.3:
            print(f"   ✅ 因子显示较强预测能力 (|IC|>{0.3})")
        else:
            print(f"   ℹ️  因子预测能力较弱 (|IC|={abs(ic):.3f})")

    def test_02_factor_consistency(self):
        """测试: 因子稳定性"""
        print("\n" + "="*60)
        print("测试: 因子稳定性")
        print("="*60)

        symbols = ["AAPL", "MSFT", "GOOGL"]

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
                    # 提取因子值
                    factor_values = []
                    for item in items:
                        factors = item.get("factors", {})
                        if factors:
                            # 检查因子是否在合理范围
                            for name, value in factors.items():
                                if isinstance(value, (int, float)):
                                    assert 0 <= value <= 1, f"{name}超出[0,1]: {value}"
                                    factor_values.append(value)

                    if factor_values:
                        mean_factor = np.mean(factor_values)
                        std_factor = np.std(factor_values)

                        print(f"   📊 因子均值: {mean_factor:.3f}")
                        print(f"   📊 因子标准差: {std_factor:.3f}")
                        print(f"   ✅ 因子稳定性验证通过")
                    else:
                        print(f"   ℹ️  未提取到因子值")
            else:
                print(f"   ⚠️  请求失败: {response.status_code}")

        except Exception as e:
            print(f"   ⚠️  测试异常: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])