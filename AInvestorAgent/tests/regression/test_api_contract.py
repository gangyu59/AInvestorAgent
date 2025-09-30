"""API契约测试"""
import pytest
import requests

class TestAPIContract:
    def test_response_schema(self, base_url):
        print("\n测试: 响应Schema")
        response = requests.get(f"{base_url}/health")
        assert "status" in response.json()
        print("   ✅ Schema验证通过")
