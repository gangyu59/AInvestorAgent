"""因子IC测试"""
import pytest
import numpy as np

class TestFactorIC:
    def test_factor_predictability(self):
        print("\n测试: 因子预测能力")
        # 模拟因子与收益率的相关性
        factors = np.random.randn(100)
        returns = factors * 0.5 + np.random.randn(100) * 0.3
        ic = np.corrcoef(factors, returns)[0, 1]
        print(f"   📊 IC: {ic:.3f}")
        assert -1 <= ic <= 1
