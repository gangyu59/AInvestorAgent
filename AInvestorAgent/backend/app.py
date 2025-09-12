from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .storage.db import engine, Base
from .api.routers.health import router as health_router
from .api.routers.prices import router as prices_router

# 自动建表（SQLite 简化）
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AInvestorAgent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True,
)

app.include_router(health_router)   # /api/health 与 /health（你已就绪）
app.include_router(prices_router)   # 关键：挂上 /api/prices/*
