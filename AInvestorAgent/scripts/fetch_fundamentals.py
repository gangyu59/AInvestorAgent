#!/usr/bin/env python3
"""
获取股票基本面数据并保存到数据库
修复版：匹配数据库表结构
"""
import os
import sys
import time
import argparse
from datetime import date, datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.db import session_scope
from backend.storage.models import Fundamental
from backend.ingestion.alpha_vantage_client import AlphaVantageClient
from backend.core.config import get_settings
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


def parse_float(value):
    """安全解析浮点数"""
    if value is None:
        return None
    try:
        s = str(value).strip()
        if s == "" or s.upper() in {"N/A", "NA", "NONE", "NULL", "-"}:
            return None
        # 移除逗号
        s = s.replace(",", "")
        result = float(s)
        # 检查 NaN 和 Infinity
        if result != result or result in (float("inf"), float("-inf")):
            return None
        return result
    except (ValueError, TypeError):
        return None


def fetch_and_save_fundamental(symbol: str, client: AlphaVantageClient, session):
    """获取单只股票的基本面数据并保存"""
    print(f"  正在获取 {symbol} 基本面...", end=" ")

    try:
        # 调用 AlphaVantage API
        data = client.get_company_overview(symbol)

        if not data:
            print("❌ 无数据")
            return False

        print("✅")

        # 解析数据
        as_of_date = date.today()

        # 构建 Fundamental 对象
        fundamental = Fundamental(
            symbol=symbol.upper(),
            as_of=as_of_date,
            pe=parse_float(data.get("PERatio")),
            pb=parse_float(data.get("PriceToBookRatio")),
            ps=parse_float(data.get("PriceToSalesRatioTTM")),
            roe=parse_float(data.get("ReturnOnEquityTTM")),
            roa=parse_float(data.get("ReturnOnAssetsTTM")),
            net_margin=parse_float(data.get("ProfitMargin")),
            gross_margin=parse_float(data.get("GrossProfitTTM")),  # 可能需要计算
            market_cap=parse_float(data.get("MarketCapitalization")),
            sector=data.get("Sector"),
            industry=data.get("Industry"),
            beta=parse_float(data.get("Beta")),
            dividend_yield=parse_float(data.get("DividendYield")),
        )

        # 检查是否已存在
        stmt = select(Fundamental).where(
            Fundamental.symbol == symbol.upper(),
            Fundamental.as_of == as_of_date
        )
        existing = session.execute(stmt).scalar_one_or_none()

        if existing:
            # 更新现有记录
            existing.pe = fundamental.pe
            existing.pb = fundamental.pb
            existing.ps = fundamental.ps
            existing.roe = fundamental.roe
            existing.roa = fundamental.roa
            existing.net_margin = fundamental.net_margin
            existing.gross_margin = fundamental.gross_margin
            existing.market_cap = fundamental.market_cap
            existing.sector = fundamental.sector
            existing.industry = fundamental.industry
            existing.beta = fundamental.beta
            existing.dividend_yield = fundamental.dividend_yield
            print(f"    ✓ 更新现有记录")
        else:
            # 添加新记录
            session.add(fundamental)
            print(f"    ✓ 新增记录")

        session.commit()
        return True

    except IntegrityError as e:
        session.rollback()
        print(f"✗ 保存失败: {e}")
        return False
    except Exception as e:
        session.rollback()
        print(f"❌ API限流或错误: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="获取股票基本面数据")
    parser.add_argument(
        "--symbols",
        type=str,
        required=True,
        help="股票代码列表，逗号分隔 (如: AAPL,MSFT,TSLA)"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=15,
        help="API调用间隔（秒），默认15秒"
    )

    args = parser.parse_args()

    # 解析股票列表
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    if not symbols:
        print("❌ 错误: 未提供有效的股票代码")
        sys.exit(1)

    print(f"\n📊 开始获取 {len(symbols)} 只股票的基本面数据")
    print(f"\n股票列表: {', '.join(symbols)}\n")

    # 初始化客户端
    settings = get_settings()
    api_key = os.getenv("ALPHAVANTAGE_KEY") or settings.ALPHAVANTAGE_KEY
    if not api_key:
        print("❌ 错误: 未设置 ALPHAVANTAGE_KEY")
        sys.exit(1)

    client = AlphaVantageClient(api_key=api_key)

    # 统计
    success_count = 0
    fail_count = 0

    # 处理每只股票
    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] {symbol}")

        with session_scope() as session:
            if fetch_and_save_fundamental(symbol, client, session):
                success_count += 1
            else:
                fail_count += 1

        # API 限流等待（最后一个不等待）
        if i < len(symbols):
            print(f"    ⏳ 等待{args.delay}秒（API限流）...")
            time.sleep(args.delay)

    # 总结
    print("\n" + "=" * 50)
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {fail_count}")
    print("=" * 50)


if __name__ == "__main__":
    main()