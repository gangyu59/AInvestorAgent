import os

# 项目根目录（按你现有脚本保持不变）
BASE_DIR = "AInvestorAgent"

# 需要生成的目录/文件（不存在则创建；已存在则跳过）
STRUCTURE = [
    # ===== 顶层 =====
    "docs/ARCHITECTURE.md",
    "docs/FUNCTIONAL_SPEC.md",
    "docs/API_REFERENCE.md",
    "docs/DATA_DICTIONARY.md",
    "docs/UI_GUIDE.md",
    "docs/CHANGELOG.md",

    # ===== Backend Core =====
    "backend/app.py",
    "backend/core/__init__.py",
    "backend/core/config.py",
    "backend/core/logging.py",
    "backend/core/rate_limit.py",
    "backend/core/exceptions.py",

    # ===== Backend API =====
    "backend/api/__init__.py",
    "backend/api/deps.py",
    "backend/api/routers/__init__.py",
    "backend/api/routers/health.py",
    "backend/api/routers/symbols.py",
    "backend/api/routers/prices.py",
    "backend/api/routers/fundamentals.py",
    "backend/api/routers/metrics.py",          # ✅ 新增：metrics 路由
    "backend/api/routers/news.py",
    "backend/api/routers/analyze.py",
    "backend/api/routers/portfolio.py",
    "backend/api/routers/backtest.py",
    "backend/api/schemas/__init__.py",
    "backend/api/schemas/common.py",
    "backend/api/schemas/price.py",
    "backend/api/schemas/fundamentals.py",
    "backend/api/schemas/metrics.py",          # ✅ 新增：metrics Schema
    "backend/api/schemas/news.py",
    "backend/api/schemas/factors.py",
    "backend/api/schemas/score.py",
    "backend/api/schemas/portfolio.py",
    "backend/api/schemas/backtest.py",
    "backend/api/schemas/analyze.py",

    # ===== Backend Ingestion / Factors / Sentiment / Scoring / Portfolio =====
    "backend/ingestion/__init__.py",
    "backend/ingestion/alpha_vantage_client.py",
    "backend/ingestion/news_api_client.py",
    "backend/ingestion/loaders.py",
    "backend/ingestion/utils.py",

    "backend/factors/__init__.py",
    "backend/factors/transforms.py",
    "backend/factors/fundamentals.py",
    "backend/factors/momentum.py",
    "backend/factors/risk.py",
    "backend/factors/aggregator.py",

    "backend/sentiment/__init__.py",
    "backend/sentiment/clean.py",
    "backend/sentiment/llm_router.py",
    "backend/sentiment/summarize.py",
    "backend/sentiment/scorer.py",

    "backend/scoring/__init__.py",
    "backend/scoring/weights.py",
    "backend/scoring/scorer.py",

    "backend/portfolio/__init__.py",
    "backend/portfolio/constraints.py",
    "backend/portfolio/allocator.py",
    "backend/portfolio/explain.py",

    # ===== Backend Backtest / Reports / Orchestrator =====
    "backend/backtest/__init__.py",
    "backend/backtest/engine.py",
    "backend/backtest/metrics.py",
    "backend/backtest/benchmark.py",

    "backend/reports/__init__.py",
    "backend/reports/markdown.py",
    "backend/reports/pdf.py",

    "backend/orchestrator/__init__.py",
    "backend/orchestrator/pipeline.py",
    "backend/orchestrator/scheduler.py",

    # ===== Backend Storage =====
    "backend/storage/__init__.py",
    "backend/storage/db.py",
    "backend/storage/models.py",
    "backend/storage/dao.py",
    "backend/storage/migrations/env.py",
    "backend/storage/migrations/script.py.mako",

    # ===== ✅ Backend Agents（新增：你的智能体实现） =====
    "backend/agents/__init__.py",
    "backend/agents/base_agent.py",
    "backend/agents/data_ingestor.py",
    "backend/agents/data_cleaner.py",
    "backend/agents/signal_researcher.py",
    "backend/agents/backtest_engineer.py",
    "backend/agents/risk_manager.py",
    "backend/agents/portfolio_manager.py",

    # ===== Backend Tests =====
    "backend/tests/__init__.py",
    "backend/tests/test_factors.py",
    "backend/tests/test_scoring.py",
    "backend/tests/test_portfolio.py",
    "backend/tests/test_backtest.py",
    "backend/tests/test_api.py",

    # ===== DB =====
    "db/schema.sql",
    "db/backup/.keep",
    "db/exports/.keep",

    # ===== Frontend 基础骨架（保持你原有结构） =====
    "frontend/index.html",
    "frontend/public/favicon.ico",
    "frontend/public/manifest.webmanifest",
    "frontend/public/robots.txt",
    "frontend/src/main.tsx",
    "frontend/src/App.tsx",
    "frontend/src/routes/index.tsx",
    "frontend/src/routes/stock.tsx",
    "frontend/src/routes/portfolio.tsx",
    "frontend/src/routes/simulator.tsx",
    "frontend/src/components/layout/Sidebar.tsx",
    "frontend/src/components/layout/Topbar.tsx",
    "frontend/src/components/cards/SnapshotCard.tsx",
    "frontend/src/components/cards/FactorCard.tsx",
    "frontend/src/components/cards/PortfolioCard.tsx",
    "frontend/src/components/charts/PriceChart.tsx",
    "frontend/src/components/charts/RadarFactors.tsx",
    "frontend/src/components/charts/MomentumBars.tsx",
    "frontend/src/components/charts/SentimentTimeline.tsx",
    "frontend/src/components/charts/WeightsPie.tsx",
    "frontend/src/components/charts/SectorBars.tsx",
    "frontend/src/components/charts/EquityCurve.tsx",
    "frontend/src/components/tables/HoldingsTable.tsx",
    "frontend/src/components/tables/NewsTable.tsx",
    "frontend/src/components/common/Loader.tsx",
    "frontend/src/components/common/ErrorState.tsx",
    "frontend/src/components/common/Tag.tsx",
    "frontend/src/services/api.ts",
    "frontend/src/services/endpoints.ts",
    "frontend/src/state/useWatchlist.ts",
    "frontend/src/state/useTheme.ts",
    "frontend/src/styles/tailwind.css",
    "frontend/src/styles/variables.css",
    "frontend/src/styles/main.css",
    "frontend/src/styles/components.css",
    "frontend/src/styles/animations.css",
    "frontend/src/styles/responsive.css",
    "frontend/src/styles/themes.css",
    "frontend/src/assets/images/logo.svg",
    "frontend/src/assets/images/placeholder.png",
    "frontend/src/assets/fonts/.keep",
    "frontend/src/utils/format.ts",
    "frontend/src/utils/chartOptions.ts",
    "frontend/src/utils/constants.ts",
    "frontend/src/config/appConfig.ts",

    # ===== Scripts / Notebooks / Tools =====
    "scripts/fetch_prices.py",
    "scripts/fetch_fundamentals.py",
    "scripts/fetch_news.py",
    "scripts/rebuild_factors.py",
    "scripts/recompute_scores.py",
    "scripts/propose_portfolio.py",
    "scripts/run_backtest.py",

    "notebooks/FactorExploration.ipynb",
    "notebooks/SentimentSandbox.ipynb",
    "notebooks/BacktestSanityCheck.ipynb",

    "tools/export_csv.py",
    "tools/db_backup.py",
    "tools/validate_config.py",
]

def create_structure(base_dir: str, structure: list[str]) -> None:
    for path in structure:
        full_path = os.path.join(base_dir, path)
        directory = os.path.dirname(full_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(full_path):
            # .keep 空文件；其他创建空占位
            if full_path.endswith(".keep"):
                open(full_path, "a").close()
            else:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write("")  # 仅生成占位，不覆盖你已有内容
            print(f"Created: {full_path}")
        else:
            print(f"Exists:  {full_path}")

if __name__ == "__main__":
    create_structure(BASE_DIR, STRUCTURE)
