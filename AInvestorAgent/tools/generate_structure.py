import os

# 项目根目录
BASE_DIR = ".."

# === 完整的测试文件结构 ===
TEST_STRUCTURE = [
    # ============================================================
    # 顶层测试目录
    # ============================================================
    "tests/__init__.py",
    "tests/README.md",
    "tests/TESTING_GUIDE.md",
    "tests/conftest.py",  # pytest配置文件

    # 核心测试文件
    "tests/test_runner.py",  # 自动化测试执行器
    "tests/test_cases_detailed.py",  # 详细测试用例
    "tests/paper_trading_simulator.py",  # 实盘模拟器

    # Shell脚本
    "tests/run_visual_tests.sh",  # 测试启动脚本
    "tests/visual_dashboard.html",  # 可视化控制台

    # ============================================================
    # 集成测试 (Integration Tests)
    # ============================================================
    "tests/integration/__init__.py",
    "tests/integration/test_end_to_end.py",  # 端到端决策流程
    "tests/integration/test_api_integration.py",  # API集成测试
    "tests/integration/test_agent_pipeline.py",  # 智能体管道测试
    "tests/integration/test_orchestrator_flow.py",  # 编排器流程测试

    # ============================================================
    # 性能测试 (Performance Tests)
    # ============================================================
    "tests/performance/__init__.py",
    "tests/performance/test_latency.py",  # 延迟测试
    "tests/performance/test_concurrent.py",  # 并发测试
    "tests/performance/test_throughput.py",  # 吞吐量测试
    "tests/performance/locustfile.py",  # Locust压测脚本
    "tests/performance/performance_report.py",  # 性能报告生成器

    # ============================================================
    # 数据验证测试 (Validation Tests)
    # ============================================================
    "tests/validation/__init__.py",
    "tests/validation/test_data_quality.py",  # 数据质量测试
    "tests/validation/test_factor_ic.py",  # 因子IC测试
    "tests/validation/test_backtest_accuracy.py",  # 回测准确性测试
    "tests/validation/test_data_consistency.py",  # 数据一致性测试
    "tests/validation/test_sentiment_accuracy.py",  # 情绪准确性测试

    # ============================================================
    # 智能体测试 (Agent Tests)
    # ============================================================
    "tests/agents/__init__.py",
    "tests/agents/test_all_agents.py",  # 所有智能体测试
    "tests/agents/test_agent_coordination.py",  # 智能体协调测试
    "tests/agents/test_data_ingestor.py",  # 数据获取智能体
    "tests/agents/test_data_cleaner.py",  # 数据清洗智能体
    "tests/agents/test_signal_researcher.py",  # 信号研究智能体
    "tests/agents/test_risk_manager.py",  # 风险管理智能体
    "tests/agents/test_portfolio_manager.py",  # 组合管理智能体
    "tests/agents/test_backtest_engineer.py",  # 回测工程师智能体

    # ============================================================
    # UI/前端测试 (UI Tests)
    # ============================================================
    "tests/ui/__init__.py",
    "tests/ui/test_navigation.py",  # 导航测试
    "tests/ui/test_charts.py",  # 图表测试
    "tests/ui/test_responsiveness.py",  # 响应式测试
    "tests/ui/test_homepage.py",  # 首页测试
    "tests/ui/test_stock_page.py",  # 个股页测试
    "tests/ui/test_portfolio_page.py",  # 组合页测试
    "tests/ui/test_simulator_page.py",  # 模拟器页测试

    # ============================================================
    # 安全测试 (Security Tests)
    # ============================================================
    "tests/security/__init__.py",
    "tests/security/test_injection.py",  # 注入攻击测试
    "tests/security/test_authentication.py",  # 认证测试
    "tests/security/test_authorization.py",  # 授权测试
    "tests/security/test_xss.py",  # XSS测试
    "tests/security/test_data_sanitization.py",  # 数据清理测试

    # ============================================================
    # 压力测试 (Stress Tests)
    # ============================================================
    "tests/stress/__init__.py",
    "tests/stress/test_extreme_scenarios.py",  # 极端场景测试
    "tests/stress/test_failure_recovery.py",  # 故障恢复测试
    "tests/stress/test_market_crash.py",  # 市场崩盘测试
    "tests/stress/test_data_overflow.py",  # 数据溢出测试
    "tests/stress/test_resource_exhaustion.py",  # 资源耗尽测试

    # ============================================================
    # 回归测试 (Regression Tests)
    # ============================================================
    "tests/regression/__init__.py",
    "tests/regression/test_scores_snapshot.py",  # 评分快照测试
    "tests/regression/test_portfolio_snapshot.py",  # 组合快照测试
    "tests/regression/test_api_contract.py",  # API契约测试
    "tests/regression/snapshots/.keep",  # 快照存储目录

    # ============================================================
    # 测试工具 (Test Utilities)
    # ============================================================
    "tests/utils/__init__.py",
    "tests/utils/data_factory.py",  # 测试数据工厂
    "tests/utils/mocks.py",  # Mock对象
    "tests/utils/fixtures.py",  # 测试夹具
    "tests/utils/helpers.py",  # 辅助函数
    "tests/utils/assertions.py",  # 自定义断言

    # ============================================================
    # 测试数据 (Test Data)
    # ============================================================
    "tests/data/__init__.py",
    "tests/data/sample_prices.json",  # 示例价格数据
    "tests/data/sample_news.json",  # 示例新闻数据
    "tests/data/sample_fundamentals.json",  # 示例基本面数据
    "tests/data/mock_responses.json",  # Mock响应数据

    # ============================================================
    # 测试报告目录 (Test Reports)
    # ============================================================
    "tests/reports/.keep",  # 报告输出目录
    "tests/logs/.keep",  # 日志目录

    # ============================================================
    # 测试配置 (Test Configuration)
    # ============================================================
    "tests/pytest.ini",  # pytest配置
    "tests/.coveragerc",  # 代码覆盖率配置
    "tests/tox.ini",  # tox配置（可选）
]

# === 后端现有测试（保留） ===
BACKEND_TESTS = [
    "backend/tests/__init__.py",
    "backend/tests/conftest.py",
    "backend/tests/test_api.py",
    "backend/tests/test_backtest.py",
    "backend/tests/test_factors.py",
    "backend/tests/test_portfolio.py",
    "backend/tests/test_scoring.py",
    "backend/tests/test_api_metrics.py",
    "backend/tests/test_api_fundamentals_mock.py",
    "backend/tests/test_agents_pipeline.py",

    # 回归测试
    "backend/tests/regression/test_scores_snapshot.py",
    "backend/tests/regression/snapshots/scores_AAPL.json",

    # 测试工具
    "backend/tests/utils/data_factory.py",
    "backend/tests/utils/mocks.py",
]

# 合并所有文件
ALL_STRUCTURE = list(dict.fromkeys(TEST_STRUCTURE + BACKEND_TESTS))


def create_structure(base_dir: str, structure: list) -> None:
    """创建文件结构"""
    created_count = 0
    exists_count = 0

    for path in structure:
        full_path = os.path.join(base_dir, path)
        directory = os.path.dirname(full_path)

        # 创建目录
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"📁 Created dir:  {directory}")

        # 创建文件
        if not os.path.exists(full_path):
            # 特殊文件处理
            if full_path.endswith(".keep"):
                # .keep文件为空
                open(full_path, "a").close()
            elif full_path.endswith(".json"):
                # JSON文件初始化为空对象
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write("{}\n")
            elif full_path.endswith("__init__.py"):
                # __init__.py添加注释
                with open(full_path, "w", encoding="utf-8") as f:
                    module_name = os.path.basename(os.path.dirname(full_path))
                    f.write(f'"""{module_name} module"""\n')
            elif full_path.endswith(".sh"):
                # Shell脚本添加shebang
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write("#!/bin/bash\n\n# TODO: Implement\n")
                # 添加执行权限
                os.chmod(full_path, 0o755)
            elif full_path.endswith(".md"):
                # Markdown文件添加标题
                filename = os.path.basename(full_path)
                title = filename.replace(".md", "").replace("_", " ").title()
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n\nTODO: Add content\n")
            elif full_path.endswith(".py"):
                # Python文件添加文档字符串
                filename = os.path.basename(full_path).replace(".py", "")
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(f'"""\n{filename}\nTODO: Implement tests\n"""\n')
            else:
                # 其他文件为空
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write("")

            print(f"✅ Created file: {full_path}")
            created_count += 1
        else:
            print(f"⚪ Exists:       {full_path}")
            exists_count += 1

    print("\n" + "=" * 60)
    print(f"📊 Summary:")
    print(f"   ✅ Created: {created_count} files")
    print(f"   ⚪ Existed: {exists_count} files")
    print(f"   📦 Total:   {created_count + exists_count} files")
    print("=" * 60)


def create_pytest_ini(base_dir: str):
    """创建pytest配置文件"""
    pytest_ini_path = os.path.join(base_dir, "tests/pytest.ini")
    content = """[pytest]
# Pytest配置文件

# 测试路径
testpaths = .

# 文件匹配模式
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 输出选项
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=backend
    --cov-report=html
    --cov-report=term-missing
    --html=reports/test_report.html
    --self-contained-html

# 标记
markers =
    slow: 慢速测试（>5秒）
    integration: 集成测试
    performance: 性能测试
    ui: UI测试
    security: 安全测试
    stress: 压力测试
    smoke: 冒烟测试
    regression: 回归测试

# 日志
log_cli = true
log_cli_level = INFO
log_file = logs/pytest.log
log_file_level = DEBUG

# 覆盖率
[coverage:run]
source = backend
omit = 
    */tests/*
    */migrations/*
    */__init__.py

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
"""
    with open(pytest_ini_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Created: {pytest_ini_path}")


def create_coveragerc(base_dir: str):
    """创建覆盖率配置文件"""
    coveragerc_path = os.path.join(base_dir, "tests/.coveragerc")
    content = """[run]
source = backend
omit =
    */tests/*
    */migrations/*
    */__init__.py
    */venv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod

[html]
directory = tests/reports/coverage_html
"""
    with open(coveragerc_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Created: {coveragerc_path}")


def create_conftest(base_dir: str):
    """创建顶层conftest.py"""
    conftest_path = os.path.join(base_dir, "tests/conftest.py")
    content = '''"""
Pytest配置和共享fixtures
"""
import sys
from pathlib import Path

# 添加backend到Python路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 测试数据库配置
TEST_DB_URL = "sqlite:///./tests/test_stock.sqlite"


@pytest.fixture(scope="session")
def test_db_engine():
    """创建测试数据库引擎"""
    engine = create_engine(TEST_DB_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_db_engine):
    """创建测试数据库会话"""
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="session")
def test_symbols():
    """测试用股票代码"""
    return ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]


@pytest.fixture(scope="session")
def base_url():
    """API基础URL"""
    return "http://localhost:8000"


@pytest.fixture
def mock_price_data():
    """模拟价格数据"""
    return {
        "dates": ["2025-01-01", "2025-01-02", "2025-01-03"],
        "prices": [
            {"open": 180.0, "high": 182.0, "low": 179.0, "close": 181.0, "volume": 1000000},
            {"open": 181.0, "high": 183.0, "low": 180.0, "close": 182.5, "volume": 1200000},
            {"open": 182.5, "high": 185.0, "low": 182.0, "close": 184.0, "volume": 1500000},
        ]
    }


@pytest.fixture
def mock_news_data():
    """模拟新闻数据"""
    return {
        "items": [
            {
                "title": "Company reports strong earnings",
                "summary": "Revenue up 20% year over year",
                "sentiment": 0.8,
                "published_at": "2025-01-01T10:00:00"
            }
        ]
    }
'''
    with open(conftest_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Created: {conftest_path}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 生成 AInvestorAgent 测试文件结构")
    print("=" * 60 + "\n")

    # 创建文件结构
    create_structure(BASE_DIR, ALL_STRUCTURE)

    print("\n" + "=" * 60)
    print("📝 生成配置文件")
    print("=" * 60 + "\n")

    # 创建配置文件
    create_pytest_ini(BASE_DIR)
    create_coveragerc(BASE_DIR)
    create_conftest(BASE_DIR)

    print("\n" + "=" * 60)
    print("✅ 完成！测试文件结构已生成")
    print("=" * 60)
    print("\n📖 下一步:")
    print("   1. 查看 tests/README.md 了解测试系统")
    print("   2. 运行 ./tests/run_visual_tests.sh --quick 进行快速测试")
    print("   3. 逐个填充测试用例代码")
    print("")