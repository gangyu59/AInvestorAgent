"""SQL注入测试"""
import pytest
import requests

class TestSQLInjection:
    def test_sql_injection_protection(self, base_url):
        print("\n测试: SQL注入防护")
        malicious = "AAPL'; DROP TABLE users; --"
        response = requests.get(f"{base_url}/api/prices/{malicious}")
        assert response.status_code in [400, 404]
        print("   ✅ SQL注入防护有效")
