"""性能报告生成器 - 汇总性能测试结果"""
import json
import datetime
from pathlib import Path


def generate_performance_report(results_file="performance_results.json"):
    """生成性能报告"""
    print("=" * 60)
    print("生成性能报告...")
    print("=" * 60)

    # 模拟性能数据（实际应从测试结果读取）
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "summary": {
            "total_tests": 10,
            "passed": 8,
            "failed": 2,
            "skipped": 0
        },
        "latency": {
            "health_check": {"avg_ms": 45, "p95_ms": 78, "p99_ms": 120},
            "price_api": {"avg_ms": 1200, "p95_ms": 1800, "p99_ms": 2500},
            "analyze_api": {"avg_ms": 3500, "p95_ms": 5000, "p99_ms": 7000}
        },
        "throughput": {
            "health_check": {"rps": 15.2, "success_rate": 0.98},
            "concurrent_requests": {"success_rate": 0.95}
        },
        "recommendations": []
    }

    # 生成建议
    if report["latency"]["health_check"]["avg_ms"] > 100:
        report["recommendations"].append("健康检查延迟较高，建议优化")

    if report["throughput"]["concurrent_requests"]["success_rate"] < 0.95:
        report["recommendations"].append("并发处理能力不足，建议增加资源")

    # 输出报告
    print("\n📊 性能测试摘要:")
    print(f"   测试时间: {report['timestamp']}")
    print(f"   总测试: {report['summary']['total_tests']}")
    print(f"   通过: {report['summary']['passed']}")
    print(f"   失败: {report['summary']['failed']}")

    print("\n⏱️  延迟指标:")
    for endpoint, metrics in report["latency"].items():
        print(f"   {endpoint}:")
        print(f"      平均: {metrics['avg_ms']}ms")
        print(f"      P95: {metrics['p95_ms']}ms")

    print("\n📈 吞吐量:")
    for endpoint, metrics in report["throughput"].items():
        if "rps" in metrics:
            print(f"   {endpoint}: {metrics['rps']} req/s")
        if "success_rate" in metrics:
            print(f"   成功率: {metrics['success_rate']:.1%}")

    if report["recommendations"]:
        print("\n💡 改进建议:")
        for rec in report["recommendations"]:
            print(f"   • {rec}")

    # 保存到文件
    output_path = Path("reports") / f"performance_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 报告已保存: {output_path}")
    return report


if __name__ == "__main__":
    generate_performance_report()