"""
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
