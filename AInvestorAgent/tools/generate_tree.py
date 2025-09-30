import os
from pathlib import Path


def generate_tree(directory, prefix="", output_file=None,
                  exclude_dirs={'.git', '__pycache__', 'node_modules', 'htmlcov', '.pytest_cache', 'dist', 'build'},
                  include_extensions={'.py', '.js', '.tsx', '.ts', '.json', '.md', '.html', '.css', '.txt', '.sh'}):
    lines = []

    try:
        entries = sorted(Path(directory).iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        return lines

    for i, entry in enumerate(entries):
        if entry.name.startswith('.') and entry.name not in {'.env', '.gitignore'}:
            continue

        if entry.is_dir() and entry.name in exclude_dirs:
            continue

        is_last = i == len(entries) - 1
        current_prefix = "└── " if is_last else "├── "

        if entry.is_dir():
            lines.append(f"{prefix}{current_prefix}{entry.name}/")
            extension = "    " if is_last else "│   "
            lines.extend(generate_tree(entry, prefix + extension, exclude_dirs=exclude_dirs,
                                       include_extensions=include_extensions))
        else:
            if entry.suffix in include_extensions or entry.name in {'README', 'LICENSE', 'Dockerfile'}:
                lines.append(f"{prefix}{current_prefix}{entry.name}")

    return lines


# 关键修改：从tools目录向上找项目根目录
script_dir = Path(__file__).parent  # tools/
root_dir = script_dir.parent  # 项目根目录
output_path = root_dir / "docs" / "file_tree.md"

print(f"脚本位置: {script_dir}")
print(f"项目根目录: {root_dir}")
print("正在生成文件树...")

tree_lines = generate_tree(root_dir)

# 确保docs目录存在
output_path.parent.mkdir(exist_ok=True)

# 写入文件
with open(output_path, "w", encoding="utf-8") as f:
    f.write("# AInvestorAgent 文件结构\n\n")
    f.write("```\n")
    f.write("AInvestorAgent/\n")
    f.write("\n".join(tree_lines))
    f.write("\n```\n")

print(f"✅ 文件树已生成: {output_path}")
print(f"📊 共 {len(tree_lines)} 个文件/目录")