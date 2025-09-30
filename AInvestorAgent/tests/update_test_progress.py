#!/usr/bin/env python3
"""
测试进度更新工具
自动运行测试并更新 test_progress.json
"""
import subprocess
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class TestProgressTracker:
    def __init__(self, progress_file="test_progress.json"):
        self.progress_file = progress_file
        self.progress_data = self.load_progress()

    def load_progress(self) -> Dict:
        """加载进度文件"""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self.create_empty_progress()

    def save_progress(self):
        """保存进度文件"""
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.progress_data, f, indent=2, ensure_ascii=False)
        print(f"✅ 进度已保存到 {self.progress_file}")

    def create_empty_progress(self) -> Dict:
        """创建空进度结构"""
        return {
            "meta": {
                "last_updated": datetime.now().isoformat(),
                "total_tests": 40,
                "passed": 0,
                "failed": 0,
                "pending": 40,
                "pass_rate": 0
            },
            "suites": {},
            "milestones": {},
            "daily_goals": {}
        }

    def run_single_test(self, test_path: str) -> Dict:
        """运行单个测试文件"""
        print(f"\n{'=' * 60}")
        print(f"🧪 运行: {test_path}")
        print('=' * 60)

        cmd = ["pytest", test_path, "-v", "--tb=short", "-q"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            stdout = result.stdout
            stderr = result.stderr

            # 解析结果
            passed = "passed" in stdout.lower() or result.returncode == 0

            # 提取通过/失败数量
            passed_count = stdout.count(" PASSED")
            failed_count = stdout.count(" FAILED")

            # 提取耗时
            duration = "0s"
            for line in stdout.split('\n'):
                if 'seconds' in line or 'second' in line:
                    try:
                        duration = line.split()[0].replace('=', '').strip()
                    except:
                        pass

            status = "passed" if passed and failed_count == 0 else "failed" if failed_count > 0 else "partial"

            return {
                "status": status,
                "last_run": datetime.now().isoformat(),
                "duration": duration,
                "passed_cases": passed_count,
                "failed_cases": failed_count,
                "returncode": result.returncode,
                "summary": stdout[-200:] if stdout else stderr[-200:]
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "last_run": datetime.now().isoformat(),
                "duration": "60s",
                "error": "测试超时"
            }
        except Exception as e:
            return {
                "status": "error",
                "last_run": datetime.now().isoformat(),
                "error": str(e)
            }

    def run_test_suite(self, suite_path: str):
        """运行整个测试套件"""
        suite_dir = Path(suite_path)
        if not suite_dir.exists():
            print(f"❌ 目录不存在: {suite_path}")
            return

        test_files = list(suite_dir.glob("test_*.py"))

        if not test_files:
            print(f"⚠️  未找到测试文件: {suite_path}")
            return

        print(f"\n📦 测试套件: {suite_path}")
        print(f"   共 {len(test_files)} 个测试文件\n")

        results = {}
        for test_file in test_files:
            result = self.run_single_test(str(test_file))
            results[test_file.name] = result

            # 打印结果
            status_icon = {
                "passed": "✅",
                "failed": "❌",
                "partial": "🟡",
                "timeout": "⏱️",
                "error": "💥"
            }
            icon = status_icon.get(result["status"], "❓")
            print(f"   {icon} {test_file.name}: {result['status']} ({result.get('duration', 'N/A')})")

        # 更新进度数据
        if suite_path not in self.progress_data["suites"]:
            self.progress_data["suites"][suite_path] = {"tests": {}}

        self.progress_data["suites"][suite_path]["tests"].update(results)
        self.update_meta_stats()
        self.save_progress()

    def run_all_tests(self):
        """运行所有测试"""
        suites = [
            "tests/agents",
            "tests/integration",
            "tests/validation",
            "tests/regression",
            "tests/performance",
            "tests/stress",
            "tests/security",
            "tests/ui"
        ]

        for suite in suites:
            if os.path.exists(suite):
                self.run_test_suite(suite)
            else:
                print(f"⏭️  跳过不存在的套件: {suite}")

        self.print_summary()

    def update_meta_stats(self):
        """更新统计信息"""
        total_passed = 0
        total_failed = 0
        total_pending = 0

        for suite_name, suite_data in self.progress_data["suites"].items():
            for test_name, test_data in suite_data.get("tests", {}).items():
                status = test_data.get("status", "pending")
                if status == "passed":
                    total_passed += 1
                elif status in ["failed", "timeout", "error"]:
                    total_failed += 1
                else:
                    total_pending += 1

        total = total_passed + total_failed + total_pending
        pass_rate = (total_passed / total * 100) if total > 0 else 0

        self.progress_data["meta"] = {
            "last_updated": datetime.now().isoformat(),
            "total_tests": total,
            "passed": total_passed,
            "failed": total_failed,
            "pending": total_pending,
            "pass_rate": round(pass_rate, 1)
        }

    def print_summary(self):
        """打印测试摘要"""
        meta = self.progress_data["meta"]

        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)
        print(f"总测试数: {meta['total_tests']}")
        print(f"✅ 通过: {meta['passed']}")
        print(f"❌ 失败: {meta['failed']}")
        print(f"⏳ 待完成: {meta['pending']}")
        print(f"📈 通过率: {meta['pass_rate']}%")
        print("=" * 60)

        # 按套件统计
        print("\n📦 各套件状态:")
        for suite_name, suite_data in self.progress_data["suites"].items():
            tests = suite_data.get("tests", {})
            passed = sum(1 for t in tests.values() if t.get("status") == "passed")
            total = len(tests)
            print(f"   {suite_name}: {passed}/{total} 通过")

    def generate_report(self, output_file="test_report.md"):
        """生成 Markdown 报告"""
        meta = self.progress_data["meta"]

        report = f"""# 测试进度报告

**更新时间**: {meta['last_updated']}

## 📊 总体统计

| 指标 | 数值 |
|------|------|
| 总测试数 | {meta['total_tests']} |
| ✅ 通过 | {meta['passed']} |
| ❌ 失败 | {meta['failed']} |
| ⏳ 待完成 | {meta['pending']} |
| 📈 通过率 | {meta['pass_rate']}% |

## 🗂️ 各套件详情

"""

        for suite_name, suite_data in self.progress_data["suites"].items():
            tests = suite_data.get("tests", {})
            report += f"\n### {suite_name}\n\n"

            for test_name, test_data in tests.items():
                status = test_data.get("status", "pending")
                icon = {"passed": "✅", "failed": "❌", "partial": "🟡"}.get(status, "⏳")
                duration = test_data.get("duration", "N/A")
                report += f"- {icon} **{test_name}** - {status} ({duration})\n"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n📝 报告已生成: {output_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="测试进度追踪工具")
    parser.add_argument("--suite", help="运行指定测试套件（如 tests/agents）")
    parser.add_argument("--test", help="运行单个测试文件")
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--summary", action="store_true", help="显示摘要")

    args = parser.parse_args()

    tracker = TestProgressTracker()

    if args.test:
        result = tracker.run_single_test(args.test)
        print(f"\n结果: {result}")
        tracker.save_progress()

    elif args.suite:
        tracker.run_test_suite(args.suite)

    elif args.all:
        tracker.run_all_tests()

    elif args.report:
        tracker.generate_report()

    elif args.summary:
        tracker.print_summary()

    else:
        print("请指定操作:")
        print("  --test <文件>   运行单个测试")
        print("  --suite <目录>  运行测试套件")
        print("  --all           运行所有测试")
        print("  --report        生成报告")
        print("  --summary       显示摘要")


if __name__ == "__main__":
    main()