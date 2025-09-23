from datetime import datetime, timedelta
from typing import Iterable, List, Dict
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from .models import PriceDaily, RunHistory

def upsert_prices_daily(db: Session, rows: Iterable[Dict]) -> int:
    # 1) 取出 ORM 实际列名
    model_cols = {c.name for c in PriceDaily.__table__.columns}

    # 2) 定义“源字段 -> 可能的目标别名”候选（按优先级从左到右）
    alias_map = {
        "dividend_amount": ["dividend_amount", "dividend", "dividendAmount"],
        "split_coefficient": ["split_coefficient", "split_coef", "splitCoefficient", "splitCoeff"],
    }

    def remap_and_filter(r: Dict) -> Dict:
        r2: Dict = {}
        for k, v in r.items():
            if k in model_cols:
                r2[k] = v
                continue
            # 尝试别名
            if k in alias_map:
                for cand in alias_map[k]:
                    if cand in model_cols:
                        r2[cand] = v
                        break
                else:
                    # 没找到可用别名就跳过该字段
                    pass
            else:
                # 其它未知字段直接丢弃（避免 invalid kw）
                pass
        return r2

    count = 0
    for r in rows:
        r_use = remap_and_filter(r)
        # 主键字段必须在（symbol, date）
        sym = r_use.get("symbol") or r.get("symbol")
        dt = r_use.get("date") or r.get("date")
        if not sym or not dt:
            continue

        stmt = select(PriceDaily).where(and_(PriceDaily.symbol == sym, PriceDaily.date == dt))
        obj = db.execute(stmt).scalar_one_or_none()
        if obj:
            # 只更新模型里存在的列
            for k, v in r_use.items():
                setattr(obj, k, v)
        else:
            obj = PriceDaily(**r_use)
            db.add(obj)
        count += 1
    return count


def get_prices_daily(db: Session, symbol: str, limit: int = 100) -> List[PriceDaily]:
    stmt = (
        select(PriceDaily)
        .where(PriceDaily.symbol == symbol.upper())
        .order_by(PriceDaily.date.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars())

def record_run(db: Session, job: str) -> None:
    db.add(RunHistory(job=job, ts=datetime.utcnow()))

def runs_last_week(db: Session, job: str) -> int:
    since = datetime.utcnow() - timedelta(days=7)
    stmt = select(func.count()).select_from(RunHistory).where(
        and_(RunHistory.job == job, RunHistory.ts >= since)
    )
    return int(db.execute(stmt).scalar() or 0)


# === 追加开始：ScoresDAO ===
# backend/storage/dao.py
from datetime import datetime
from sqlalchemy import and_
from .models import ScoreDaily   # 你已有的 ORM 模型

# AInvestorAgent/backend/storage/dao.py （节选：替换这两个方法）

class ScoresDAO:
    @staticmethod
    def upsert(payload: dict):
        """
        以 (symbol, as_of, version_tag) 唯一标识一条评分记录：
        如果已存在 -> 更新；不存在 -> 插入；
        若历史上有重复 -> 取最新一条更新，忽略其它重复。
        """
        from sqlalchemy import select
        from backend.storage.models import ScoreDaily  # 你的 ORM 模型名保持不变

        with SessionLocal() as s:
            q = (
                select(ScoreDaily)
                .where(
                    ScoreDaily.symbol == payload["symbol"],
                    ScoreDaily.as_of == payload["as_of"],
                    ScoreDaily.version_tag == payload.get("version_tag", "v1.0.0"),
                )
                .order_by(ScoreDaily.id.desc())  # 没有 updated_at 就按自增 id
            )
            rows = s.execute(q).scalars().all()
            if rows:
                row = rows[0]
                for k, v in payload.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
            else:
                row = ScoreDaily(**payload)
                s.add(row)
            s.commit()
            return row

    @staticmethod
    def get_last_success(symbol: str):
        """
        返回某个 symbol 最近一次成功评分（按 as_of 或 id 倒序）。
        """
        from sqlalchemy import select
        from backend.storage.models import ScoreDaily

        with SessionLocal() as s:
            q = (
                select(ScoreDaily)
                .where(ScoreDaily.symbol == symbol)
                .order_by(
                    getattr(ScoreDaily, "as_of", None).desc()
                    if hasattr(ScoreDaily, "as_of") else
                    ScoreDaily.id.desc()
                )
                .limit(1)
            )
            return s.execute(q).scalars().first()

