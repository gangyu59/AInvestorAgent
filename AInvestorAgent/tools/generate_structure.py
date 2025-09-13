import os

# 项目根目录（与你现有脚本保持一致）
BASE_DIR = ".."

# === 这里是“新增的测试文件清单” ===
NEW_TESTS = [
    # 顶层 tests 目录与文件
    "backend/tests/conftest.py",
    "backend/tests/test_api_metrics.py",
    "backend/tests/test_api_fundamentals_mock.py",
    "backend/tests/test_agents_pipeline.py",

    # 回归测试与快照
    "backend/tests/regression/test_scores_snapshot.py",
    "backend/tests/regression/snapshots/scores_AAPL.json",

    # 测试工具
    "backend/tests/utils/data_factory.py",
    "backend/tests/utils/mocks.py",
]

# === 如果你已经有 STRUCTURE（老清单），就沿用；否则提供一个最小兜底 ===
try:
    STRUCTURE  # noqa: F821
except NameError:
    STRUCTURE = [
        "backend/tests/__init__.py",  # 若你没有就顺便建一个
    ]

# 合并老清单 + 新测试清单（去重）
ALL = list(dict.fromkeys(STRUCTURE + NEW_TESTS))

def create_structure(base_dir: str, structure: list[str]) -> None:
    for path in structure:
        full_path = os.path.join(base_dir, path)
        directory = os.path.dirname(full_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(full_path):
            # .keep 与 .json 空文件保持空内容；其它文件创建空占位
            if full_path.endswith(".keep") or full_path.endswith(".json"):
                open(full_path, "a").close()
            else:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write("")  # 仅占位，不覆盖已有实现
            print(f"Created: {full_path}")
        else:
            print(f"Exists:  {full_path}")

if __name__ == "__main__":
    create_structure(BASE_DIR, ALL)
