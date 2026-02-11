import os
import logging
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]  # 指向项目根 AInvestorAgent/AInvestorAgent/
ENV_FILE = ROOT_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=False)

# 添加 logger 配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
from backend.api.routers import analyze
from backend.api.routers import sentiment
from backend.api.routers import llm as llm_router_api
from backend.api.routers import decide
from backend.api.routers import simulation
from backend.api.routers import validation
from backend.api.routers import testing
from backend.api.routers import batch_update
from backend.api.routers import symbols
from backend.api.routers import watchlist
from backend.api.routers import factors

from fastapi.staticfiles import StaticFiles

# 在现有的导入后添加
from backend.orchestrator.scheduler import investment_scheduler
from contextlib import asynccontextmanager


# 添加生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    logger.info("🚀 启动 AInvestorAgent...")

    # 可选：启动定时调度（生产环境使用）
    if os.getenv("ENABLE_SCHEDULER", "false").lower() == "true":
        investment_scheduler.start_scheduler()

    yield

    # 关闭时
    logger.info("🛑 关闭 AInvestorAgent...")
    investment_scheduler.stop_scheduler()


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
# app.include_router(backtest_router.router, prefix="/api")
app.include_router(backtest_router.router)
app.include_router(viz_router, prefix="/api")
app.include_router(trace_router, prefix="/api")
app.include_router(sim.router)
app.include_router(analyze.router, prefix="/api")
app.include_router(sentiment.router, prefix="/api")
app.include_router(llm_router_api.router)
app.include_router(decide.router)
app.include_router(simulation.router)
app.include_router(validation.router)
app.include_router(testing.router)
app.include_router(batch_update.router)
app.include_router(symbols.router)
app.include_router(watchlist.router)
app.include_router(factors.router)

app.router.lifespan_context = lifespan

# 静态挂载 /reports 以便前端能打开 last_report.html
REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORT_DIR, exist_ok=True)
app.mount("/reports", StaticFiles(directory=REPORT_DIR), name="reports")

# ==================== 前端静态文件服务 ====================
# 生产部署时，由后端直接提供前端构建产物（frontend/dist/）
# 这样 Launch.bat 只需启动一个进程（Python backend）
FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    from starlette.responses import FileResponse

    # 挂载静态资源（JS/CSS/图片等）
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend-assets")

    # SPA catch-all: 非 API 路径一律返回 index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # 排除 API 路径和已挂载的路径
        if full_path.startswith(("api/", "health", "reports/", "orchestrator/", "docs", "openapi")):
            return None  # 让 FastAPI 继续匹配其他路由
        # 检查是否是静态文件（如 favicon.ico, vite.svg 等）
        static_file = FRONTEND_DIST / full_path
        if full_path and static_file.exists() and static_file.is_file():
            return FileResponse(str(static_file))
        # 其他路径一律返回 index.html（SPA 路由）
        return FileResponse(str(FRONTEND_DIST / "index.html"))

    logger.info(f"🌐 前端已挂载: {FRONTEND_DIST}")
else:
    logger.info(f"ℹ️ 前端 dist 未找到({FRONTEND_DIST})，请运行 npm run build 或使用 vite dev server")

@app.get("/health")
def health():
    return {"status": "ok"}


