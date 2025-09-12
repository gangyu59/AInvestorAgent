from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from ...storage.db import SessionLocal, Base, engine
from ...storage.dao import get_prices_daily, record_run, runs_last_week, upsert_prices_daily
from ...api.schemas.price import PriceSeriesResponse, PriceBar
from ...ingestion.loaders import load_daily_from_alpha

# 固定前缀：/api/prices
router = APIRouter(prefix="/api/prices", tags=["prices"])

# 确保表存在（SQLite 简化；若你用 Alembic，可删掉此行）
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/daily", response_model=PriceSeriesResponse)
def daily_prices(
    symbol: str = Query(..., min_length=1),
    limit: int = Query(100, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    rows = get_prices_daily(db, symbol, limit)

    def to_pricebar(o) -> PriceBar:
        # 统一从 ORM 对象上获取字段，带别名和默认值兜底
        get = getattr
        return PriceBar(
            symbol=get(o, "symbol"),
            date=get(o, "date"),
            open=float(get(o, "open") or 0.0),
            high=float(get(o, "high") or 0.0),
            low=float(get(o, "low") or 0.0),
            close=float(get(o, "close") or 0.0),
            volume=int(get(o, "volume") or 0),
            # 列名兼容：dividend_amount / dividend / dividendAmount
            dividend_amount=float(
                (get(o, "dividend_amount", None)
                 or get(o, "dividend", None)
                 or get(o, "dividendAmount", None)
                 or 0.0)
            ),
            # 列名兼容：split_coefficient / split_coef / splitCoefficient
            split_coefficient=float(
                (get(o, "split_coefficient", None)
                 or get(o, "split_coef", None)
                 or get(o, "splitCoefficient", None)
                 or 1.0)
            ),
        )

    # 升序返回
    items = [to_pricebar(r) for r in reversed(rows)]
    return {"symbol": symbol.upper(), "items": items}


@router.post("/fetch")
def fetch_and_store_daily(
    symbol: str = Query(..., min_length=1),
    adjusted: bool = Query(True),
    outputsize: str = Query("compact", pattern="^(compact|full)$"),
    db: Session = Depends(get_db),
):
    job = f"fetch_daily:{symbol.upper()}"
    if runs_last_week(db, job) >= 3:
        raise HTTPException(status_code=429, detail="本任务已达到每周 3 次上限")
    try:
        n = load_daily_from_alpha(db, symbol, adjusted=adjusted, outputsize=outputsize)
        record_run(db, job)
        db.commit()
        return {"symbol": symbol.upper(), "inserted_or_updated": n}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
