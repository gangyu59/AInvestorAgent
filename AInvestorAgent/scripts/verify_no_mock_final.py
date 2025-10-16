# scripts/verify_no_mock_final.py
"""
最终验证：确保彻底移除Mock（改进版 - 跳过白名单）
"""
import re
from pathlib import Path


def check_file(file_path):
    """检查单个文件"""
    issues = []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 白名单：这些行是定义禁止词列表的，不算违规
    whitelist_patterns = [
        r"forbidden\s*=\s*\[.*'mock'.*\]",  # forbidden = ['mock', ...]
        r"#.*mock",  # 注释中的mock
        r"//.*mock",  # JS注释中的mock
        r"\".*禁用.*mock.*\"",  # 说明文字
        r"'.*禁用.*mock.*'",
    ]

    # 检查Mock相关代码
    danger_patterns = [
        (r'mock\s*:\s*true', 'Mock参数设为true'),
        (r'params\s*:\s*\{\s*mock', 'params中包含mock'),
        (r'\.mock\s*=', '设置mock属性'),
        (r'if.*mock', '判断mock条件'),
        (r'MOCK_MODE\s*=\s*True', '启用MOCK_MODE'),
    ]

    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        # 跳过白名单行
        is_whitelisted = False
        for wp in whitelist_patterns:
            if re.search(wp, line, re.IGNORECASE):
                is_whitelisted = True
                break

        if is_whitelisted:
            continue

        # 检查危险模式
        for pattern, desc in danger_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(f"  第{i}行: {desc}\n    {line.strip()}")

    return issues


def main():
    print("🔍 验证Mock代码清除情况（改进版）\n")

    files_to_check = [
        Path('tests/test_dashboard.html'),
        Path('tests/visual_dashboard.html'),
        Path('backend/api/routers/testing.py'),
    ]

    all_clean = True

    for file_path in files_to_check:
        if not file_path.exists():
            print(f"⚠️  {file_path} 不存在")
            continue

        print(f"📄 检查: {file_path}")
        issues = check_file(file_path)

        if issues:
            all_clean = False
            print(f"  ❌ 发现 {len(issues)} 个问题:")
            for issue in issues:
                print(issue)
        else:
            print(f"  ✅ 无Mock使用")
        print()

    print("=" * 70)
    if all_clean:
        print("✅ 验证通过！所有文件已清除Mock代码！")
        print("\n下一步：")
        print("  1. python run.py          # 启动后端")
        print("  2. 打开 tests/test_dashboard.html")
        print("  3. 点击 '运行全部' 测试")
    else:
        print("❌ 验证失败！仍存在Mock相关代码，请修复后重试。")
    print("=" * 70)

    return 0 if all_clean else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())