import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.storage.db import engine, Base
from backend.api.routers.health import router as health_router
from backend.api.routers.prices import router as prices_router
from backend.api.routers import news as news_router
from fastapi.staticfiles import StaticFiles
from backend.api.routers import qa  # 新增
from backend.api.routers import metrics, fundamentals
from backend.api.routers import scores as scores_router
from backend.api.routers import portfolio as portfolio_router
from backend.api.routers import orchestrator as orchestrator_router
from backend.api.routers import backtest as backtest_router
from backend.api.viz import router as viz_router
from backend.api.trace import router as trace_router
from backend.api.routers import sim


# backend/app.py 的顶部 import 里加
from fastapi.staticfiles import StaticFiles

# 自动建表（SQLite 简化）
Base.metadata.create_all(bind=engine)

app = FastAPI()

# app.mount("/reports", StaticFiles(directory="reports"), name="reports")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True,
)

app.include_router(health_router)   # /api/health 与 /health（你已就绪）
app.include_router(prices_router)   # 关键：挂上 /api/prices/*
app.include_router(qa.router)
app.include_router(metrics.router)
app.include_router(fundamentals.router)
app.include_router(news_router.router)
app.include_router(scores_router.router)
app.include_router(portfolio_router.router)
app.include_router(orchestrator_router.router)
app.include_router(backtest_router.router)
app.include_router(viz_router, prefix="/api")
app.include_router(trace_router, prefix="/api")
app.include_router(sim.router)


# 静态挂载 /reports 以便前端能打开 last_report.html
REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORT_DIR, exist_ok=True)
app.mount("/reports", StaticFiles(directory=REPORT_DIR), name="reports")

@app.get("/health")
def health():
    return {"status": "ok"}