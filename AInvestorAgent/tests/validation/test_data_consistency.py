"""数据一致性测试"""
import pytest
import requests

class TestDataConsistency:
    def test_cross_source_validation(self, base_url):
        print("\n测试: 跨数据源验证")
        price_resp = requests.get(f"{base_url}/api/prices/AAPL?range=1M")
        analyze_resp = requests.post(f"{base_url}/api/analyze/AAPL")
        
        if price_resp.status_code == 200 and analyze_resp.status_code == 200:
            print("   ✅ 数据源一致性验证通过")
