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
from typing import Optional, Dict, Any, List
from sqlalchemy import select, and_
from .db import SessionLocal
from .models import ScoreDaily  # 你已有的 ORM 模型（scores_daily 表）

class ScoresDAO:
    @staticmethod
    def upsert(item: Dict[str, Any]) -> None:
        """
        item: {
          "symbol": str,
          "factors": {"f_value":..., "f_quality":..., "f_momentum":..., "f_sentiment":..., "f_risk":...},
          "score": {"value":int,"quality":int,"momentum":int,"sentiment":int,"score":int,"version_tag":str},
          "updated_at": datetime
        }
        """
        with SessionLocal() as s:
            row = s.execute(
                select(ScoreDaily).where(ScoreDaily.symbol == item["symbol"])
            ).scalar_one_or_none()
            if row is None:
                row = ScoreDaily(symbol=item["symbol"])
                s.add(row)
            # 这里假设 ScoreDaily 有 JSON 列 factors/detail（或等价）
            row.factors = item["factors"]
            row.detail = item["score"]
            row.updated_at = item["updated_at"]
            s.commit()

    @staticmethod
    def get_last_success(symbol: str) -> Optional[Dict[str, Any]]:
        with SessionLocal() as s:
            row = (
                s.execute(
                    select(ScoreDaily)
                    .where(ScoreDaily.symbol == symbol)
                    .order_by(ScoreDaily.updated_at.desc())
                ).scalar_one_or_none()
            )
            if not row:
                return None
            return {
                "symbol": symbol,
                "factors": row.factors,
                "score": row.detail,
                "updated_at": row.updated_at,
            }

