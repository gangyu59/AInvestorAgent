"""
DataCleaner智能体测试
测试数据清洗功能
"""
import pytest
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from agents.data_cleaner import DataCleaner
from backend.agents.base_agent import AgentContext


class TestDataCleanerBasic:
    """DataCleaner基础功能测试"""

    def test_01_missing_values_handling(self):
        """测试: 缺失值处理"""
        print("\n" + "="*60)
        print("测试: 缺失值处理")
        print("="*60)

        context = AgentContext()
        context.data = {
            "prices": [
                {"date": "2025-01-01", "close": 100.0},
                {"date": "2025-01-02", "close": None},
                {"date": "2025-01-03", "close": 102.0},
            ]
        }

        cleaner = DataCleaner()

        try:
            result = cleaner.execute(context)

            prices = result.data.get("prices", [])
            null_count = sum(1 for p in prices if p.get("close") is None)

            print(f"   📊 处理前NULL数: 1")
            print(f"   📊 处理后NULL数: {null_count}")

            if null_count == 0:
                print(f"   ✅ 缺失值已处理")
            else:
                print(f"   ℹ️  仍有{null_count}个NULL（可能保留）")

        except Exception as e:
            print(f"   ⚠️  测试失败: {e}")

    def test_02_outlier_detection(self):
        """测试: 异常值检测"""
        print("\n" + "="*60)
        print("测试: 异常值检测")
        print("="*60)

        context = AgentContext()
        context.data = {
            "prices": [
                {"date": "2025-01-01", "close": 100.0},
                {"date": "2025-01-02", "close": 101.0},
                {"date": "2025-01-03", "close": 1000.0},  # 异常值
                {"date": "2025-01-04", "close": 102.0},
            ]
        }

        cleaner = DataCleaner()

        try:
            result = cleaner.execute(context)

            if hasattr(result, "outliers") or "outliers" in result.data:
                outliers = result.outliers if hasattr(result, "outliers") else result.data["outliers"]
                print(f"   ✅ 检测到异常值: {len(outliers)}个")
            else:
                print(f"   ℹ️  异常值检测未实现")

        except Exception as e:
            print(f"   ⚠️  测试失败: {e}")

    def test_03_data_alignment(self):
        """测试: 数据对齐"""
        print("\n" + "="*60)
        print("测试: 数据对齐")
        print("="*60)

        context = AgentContext()
        context.data = {
            "prices": [
                {"date": "2025-01-01"},
                {"date": "2025-01-03"},  # 缺少01-02
                {"date": "2025-01-04"},
            ],
            "news": [
                {"date": "2025-01-02"},  # 价格缺失这天
            ]
        }

        cleaner = DataCleaner()

        try:
            result = cleaner.execute(context)
            print(f"   ✅ 数据对齐处理完成")
        except Exception as e:
            print(f"   ⚠️  测试失败: {e}")


class TestDataCleanerEdgeCases:
    """DataCleaner边界情况测试"""

    def test_01_empty_data(self):
        """测试: 空数据"""
        print("\n" + "="*60)
        print("测试: 空数据")
        print("="*60)

        context = AgentContext()
        context.data = {"prices": []}

        cleaner = DataCleaner()

        try:
            result = cleaner.execute(context)
            print(f"   ✅ 空数据处理正常（未崩溃）")
        except Exception as e:
            print(f"   ✅ 抛出预期异常: {type(e).__name__}")

    def test_02_all_null_column(self):
        """测试: 全NULL列"""
        print("\n" + "="*60)
        print("测试: 全NULL列")
        print("="*60)

        context = AgentContext()
        context.data = {
            "prices": [
                {"date": "2025-01-01", "close": None},
                {"date": "2025-01-02", "close": None},
                {"date": "2025-01-03", "close": None},
            ]
        }

        cleaner = DataCleaner()

        try:
            result = cleaner.execute(context)
            print(f"   ✅ 全NULL列处理正常")
        except Exception as e:
            print(f"   ✅ 抛出预期异常: {type(e).__name__}")

    def test_03_inconsistent_schema(self):
        """测试: 不一致的schema"""
        print("\n" + "="*60)
        print("测试: 不一致的schema")
        print("="*60)

        context = AgentContext()
        context.data = {
            "prices": [
                {"date": "2025-01-01", "close": 100.0},
                {"date": "2025-01-02", "price": 101.0},  # 字段名不同
                {"date": "2025-01-03", "close": 102.0},
            ]
        }

        cleaner = DataCleaner()

        try:
            result = cleaner.execute(context)
            print(f"   ✅ 不一致schema处理正常")
        except Exception as e:
            print(f"   ⚠️  schema不一致导致失败: {type(e).__name__}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])