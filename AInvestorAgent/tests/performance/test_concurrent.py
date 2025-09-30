"""并发测试"""
import pytest
import requests
import concurrent.futures

class TestConcurrentRequests:
    def test_concurrent_health_checks(self, base_url):
        print("\n测试: 并发健康检查")
        def check():
            return requests.get(f"{base_url}/health", timeout=5).status_code == 200
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        success = sum(results)
        print(f"   ✅ 成功: {success}/10")
        assert success >= 8
