# 项目文件架构

```text
AInvestorAgent/
    ├── #!/
    │   └── usr/
    │       └── bin/
    ├── .env
    ├── backend/
    │   ├── agents/
    │   │   ├── __init__.py
    │   │   ├── backtest_engineer.py
    │   │   ├── base_agent.py
    │   │   ├── data_cleaner.py
    │   │   ├── data_ingestor.py
    │   │   ├── portfolio_manager.py
    │   │   ├── risk_manager.py
    │   │   └── signal_researcher.py
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── deps.py
    │   │   ├── routers/
    │   │   │   ├── __init__.py
    │   │   │   ├── analyze.py
    │   │   │   ├── backtest.py
    │   │   │   ├── fundamentals.py
    │   │   │   ├── health.py
    │   │   │   ├── metrics.py
    │   │   │   ├── news.py
    │   │   │   ├── portfolio.py
    │   │   │   ├── prices.py
    │   │   │   └── symbols.py
    │   │   └── schemas/
    │   │       ├── __init__.py
    │   │       ├── analyze.py
    │   │       ├── backtest.py
    │   │       ├── common.py
    │   │       ├── factors.py
    │   │       ├── fundamentals.py
    │   │       ├── metrics.py
    │   │       ├── news.py
    │   │       ├── portfolio.py
    │   │       ├── price.py
    │   │       └── score.py
    │   ├── app.py
    │   ├── backtest/
    │   │   ├── __init__.py
    │   │   ├── benchmark.py
    │   │   ├── engine.py
    │   │   └── metrics.py
    │   ├── core/
    │   │   ├── __init__.py
    │   │   ├── config.py
    │   │   ├── exceptions.py
    │   │   ├── logging.py
    │   │   └── rate_limit.py
    │   ├── factors/
    │   │   ├── __init__.py
    │   │   ├── aggregator.py
    │   │   ├── fundamentals.py
    │   │   ├── momentum.py
    │   │   ├── risk.py
    │   │   └── transforms.py
    │   ├── ingestion/
    │   │   ├── __init__.py
    │   │   ├── alpha_vantage_client.py
    │   │   ├── loaders.py
    │   │   ├── news_api_client.py
    │   │   └── utils.py
    │   ├── orchestrator/
    │   │   ├── __init__.py
    │   │   ├── pipeline.py
    │   │   └── scheduler.py
    │   ├── portfolio/
    │   │   ├── __init__.py
    │   │   ├── allocator.py
    │   │   ├── constraints.py
    │   │   └── explain.py
    │   ├── reports/
    │   │   ├── __init__.py
    │   │   ├── markdown.py
    │   │   └── pdf.py
    │   ├── scoring/
    │   │   ├── __init__.py
    │   │   ├── scorer.py
    │   │   └── weights.py
    │   ├── sentiment/
    │   │   ├── __init__.py
    │   │   ├── clean.py
    │   │   ├── llm_router.py
    │   │   ├── scorer.py
    │   │   └── summarize.py
    │   ├── storage/
    │   │   ├── __init__.py
    │   │   ├── dao.py
    │   │   ├── db.py
    │   │   ├── migrations/
    │   │   │   ├── env.py
    │   │   │   └── script.py.mako
    │   │   └── models.py
    │   └── tests/
    │       ├── __init__.py
    │       ├── test_api.py
    │       ├── test_backtest.py
    │       ├── test_factors.py
    │       ├── test_portfolio.py
    │       └── test_scoring.py
    ├── db/
    │   ├── backup/
    │   │   └── .keep
    │   ├── exports/
    │   │   └── .keep
    │   ├── schema.sql
    │   └── stock.sqlite
    ├── docs/
    │   ├── API_REFERENCE.md
    │   ├── ARCHITECTURE.md
    │   ├── CHANGELOG.md
    │   ├── DATA_DICTIONARY.md
    │   ├── FUNCTIONAL_SPEC.md
    │   └── UI_GUIDE.md
    ├── frontend/
    │   ├── .env
    │   ├── .gitignore
    │   ├── README.md
    │   ├── env.d.ts
    │   ├── eslint.config.js
    │   ├── index.html
    │   ├── package-lock.json
    │   ├── package.json
    │   ├── public/
    │   │   ├── favicon.ico
    │   │   ├── manifest.webmanifest
    │   │   ├── robots.txt
    │   │   └── vite.svg
    │   ├── src/
    │   │   ├── App.css
    │   │   ├── App.tsx
    │   │   ├── assets/
    │   │   │   ├── fonts/
    │   │   │   │   └── .keep
    │   │   │   ├── images/
    │   │   │   │   ├── logo.svg
    │   │   │   │   └── placeholder.png
    │   │   │   └── react.svg
    │   │   ├── components/
    │   │   │   ├── cards/
    │   │   │   │   ├── FactorCard.tsx
    │   │   │   │   ├── KPIGrid.tsx
    │   │   │   │   ├── PortfolioCard.tsx
    │   │   │   │   └── SnapshotCard.tsx
    │   │   │   ├── charts/
    │   │   │   │   ├── EquityCurve.tsx
    │   │   │   │   ├── MomentumBars.tsx
    │   │   │   │   ├── PriceChart.tsx
    │   │   │   │   ├── RadarFactors.tsx
    │   │   │   │   ├── RequestsChart.tsx
    │   │   │   │   ├── SectorBars.tsx
    │   │   │   │   ├── SentimentTimeline.tsx
    │   │   │   │   └── WeightsPie.tsx
    │   │   │   ├── common/
    │   │   │   │   ├── ErrorState.tsx
    │   │   │   │   ├── Loader.tsx
    │   │   │   │   └── Tag.tsx
    │   │   │   ├── layout/
    │   │   │   │   ├── Sidebar.tsx
    │   │   │   │   └── Topbar.tsx
    │   │   │   └── tables/
    │   │   │       ├── EventsTable.tsx
    │   │   │       ├── HoldingsTable.tsx
    │   │   │       └── NewsTable.tsx
    │   │   ├── config/
    │   │   │   └── appConfig.ts
    │   │   ├── index.css
    │   │   ├── main.tsx
    │   │   ├── routes/
    │   │   │   ├── index.tsx
    │   │   │   ├── manage.tsx
    │   │   │   ├── monitor.tsx
    │   │   │   ├── portfolio.tsx
    │   │   │   ├── simulator.tsx
    │   │   │   └── stock.tsx
    │   │   ├── services/
    │   │   │   ├── api.ts
    │   │   │   └── endpoints.ts
    │   │   ├── state/
    │   │   │   ├── useTheme.ts
    │   │   │   └── useWatchlist.ts
    │   │   ├── styles/
    │   │   │   ├── animations.css
    │   │   │   ├── components.css
    │   │   │   ├── main.css
    │   │   │   ├── responsive.css
    │   │   │   ├── tailwind.css
    │   │   │   ├── themes.css
    │   │   │   └── variables.css
    │   │   ├── utils/
    │   │   │   ├── chartOptions.ts
    │   │   │   ├── constants.ts
    │   │   │   └── format.ts
    │   │   └── vite-env.d.ts
    │   ├── tsconfig.app.json
    │   ├── tsconfig.json
    │   ├── tsconfig.node.json
    │   └── vite.config.ts
    ├── notebooks/
    │   ├── BacktestSanityCheck.ipynb
    │   ├── FactorExploration.ipynb
    │   └── SentimentSandbox.ipynb
    ├── requirements.txt
    ├── run.py
    ├── scripts/
    │   ├── fetch_fundamentals.py
    │   ├── fetch_news.py
    │   ├── fetch_prices.py
    │   ├── propose_portfolio.py
    │   ├── rebuild_factors.py
    │   ├── recompute_scores.py
    │   └── run_backtest.py
    └── tools/
        ├── db_backup.py
        ├── export_csv.py
        └── validate_config.py
```
