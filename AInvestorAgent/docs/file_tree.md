# AInvestorAgent 文件结构

```
AInvestorAgent/
├── #!/
│   └── usr/
│       └── bin/
├── backend/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── agent_layer.py
│   │   ├── backtest_engineer.py
│   │   ├── base_agent.py
│   │   ├── chair.py
│   │   ├── data_cleaner.py
│   │   ├── data_ingestor.py
│   │   ├── earnings.py
│   │   ├── executor.py
│   │   ├── macro.py
│   │   ├── news_sentiment.py
│   │   ├── portfolio_manager.py
│   │   ├── registry.py
│   │   ├── risk_manager.py
│   │   └── signal_researcher.py
│   ├── api/
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── analyze.py
│   │   │   ├── backtest.py
│   │   │   ├── decide.py
│   │   │   ├── fundamentals.py
│   │   │   ├── health.py
│   │   │   ├── llm.py
│   │   │   ├── metrics.py
│   │   │   ├── news.py
│   │   │   ├── orchestrator.py
│   │   │   ├── portfolio.py
│   │   │   ├── prices.py
│   │   │   ├── qa.py
│   │   │   ├── scores.py
│   │   │   ├── sentiment.py
│   │   │   ├── sim.py
│   │   │   ├── simulation.py
│   │   │   ├── symbols.py
│   │   │   └── validation.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── analyze.py
│   │   │   ├── backtest.py
│   │   │   ├── common.py
│   │   │   ├── factors.py
│   │   │   ├── fundamentals.py
│   │   │   ├── metrics.py
│   │   │   ├── news.py
│   │   │   ├── portfolio.py
│   │   │   ├── price.py
│   │   │   ├── scores.py
│   │   │   └── sentiment.py
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   ├── trace.py
│   │   └── viz.py
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
│   │   ├── sentiment.py
│   │   └── transforms.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── alpha_vantage_client.py
│   │   ├── fixtures.py
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
│   │   ├── agents_smoketest.html
│   │   ├── markdown.py
│   │   ├── news_smoketest.html
│   │   ├── pdf.py
│   │   ├── portfolio_smoketest.html
│   │   ├── price_smoketest.html
│   │   ├── pytest.json
│   │   ├── scores_smoketest.html
│   │   └── unit.html
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── combine.py
│   │   ├── scorer.py
│   │   └── weights.py
│   ├── sentiment/
│   │   ├── __init__.py
│   │   ├── clean.py
│   │   ├── llm_router.py
│   │   ├── scorer.py
│   │   └── summarize.py
│   ├── sim/
│   │   └── paper.py
│   ├── simulation/
│   │   └── trading_engine.py
│   ├── storage/
│   │   ├── migrations/
│   │   │   ├── env.py
│   │   ├── __init__.py
│   │   ├── dao.py
│   │   ├── db.py
│   │   └── models.py
│   ├── tests/
│   │   ├── regression/
│   │   │   ├── snapshots/
│   │   │   │   └── scores_AAPL.json
│   │   │   └── test_scores_snapshot.py
│   │   ├── utils/
│   │   │   ├── data_factory.py
│   │   │   └── mocks.py
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_00_health_and_schema.py
│   │   ├── test_10_research_chain.py
│   │   ├── test_20_portfolio_and_risk.py
│   │   ├── test_30_backtest_weekly.py
│   │   ├── test_40_orchestrator_e2e.py
│   │   ├── test_50_resilience_and_fallbacks.py
│   │   ├── test_60_persistence_and_versions.py
│   │   ├── test_agent_macro_mock.py
│   │   ├── test_agent_news_sentiment_mock.py
│   │   ├── test_agents_pipeline.py
│   │   ├── test_agents_registry_and_layer.py
│   │   ├── test_api.py
│   │   ├── test_api_fundamentals_mock.py
│   │   ├── test_api_metrics.py
│   │   ├── test_backtest.py
│   │   ├── test_decide_api.py
│   │   ├── test_executor_diff.py
│   │   ├── test_factors.py
│   │   ├── test_news_api.py
│   │   ├── test_news_api_offline.py
│   │   ├── test_orchestrator_min.py
│   │   ├── test_pm_rm_min.py
│   │   ├── test_portfolio.py
│   │   ├── test_scoring.py
│   │   └── test_sim_run_mock.py
│   ├── __init__.py
│   └── app.py
├── backendreports/
├── db/
│   ├── backup/
│   ├── exports/
│   │   └── price_smoketest.html
├── docs/
│   ├── API_REFERENCE.md
│   ├── ARCHITECTURE.md
│   ├── CHANGELOG.md
│   ├── DATA_DICTIONARY.md
│   ├── FUNCTIONAL_SPEC.md
│   └── UI_GUIDE.md
├── frontend/
│   ├── public/
│   │   ├── robots.txt
│   ├── src/
│   │   ├── assets/
│   │   │   ├── fonts/
│   │   │   ├── images/
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
│   │   │   ├── qa/
│   │   │   │   ├── PassRateChart.tsx
│   │   │   │   ├── RecentRunsTable.tsx
│   │   │   │   └── SuiteBar.tsx
│   │   │   └── tables/
│   │   │       ├── EventsTable.tsx
│   │   │       ├── HoldingsTable.tsx
│   │   │       └── NewsTable.tsx
│   │   ├── config/
│   │   │   └── appConfig.ts
│   │   ├── routes/
│   │   │   ├── index.tsx
│   │   │   ├── manage.tsx
│   │   │   ├── monitor.tsx
│   │   │   ├── portfolio.tsx
│   │   │   ├── simulator.tsx
│   │   │   ├── stock.tsx
│   │   │   ├── test_dashboard.tsx
│   │   │   └── trading.tsx
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   ├── endpoints.ts
│   │   │   └── qa.ts
│   │   ├── state/
│   │   │   ├── useTheme.ts
│   │   │   └── useWatchlist.ts
│   │   ├── styles/
│   │   │   ├── animations.css
│   │   │   ├── components.css
│   │   │   ├── home.css
│   │   │   ├── main.css
│   │   │   ├── responsive.css
│   │   │   ├── tailwind.css
│   │   │   ├── themes.css
│   │   │   └── variables.css
│   │   ├── utils/
│   │   │   ├── chartOptions.ts
│   │   │   ├── constants.ts
│   │   │   └── format.ts
│   │   ├── App.css
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── main.tsx
│   │   └── vite-env.d.ts
│   ├── env.d.ts
│   ├── eslint.config.js
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── README.md
│   ├── tsconfig.app.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── logs/
├── notebooks/
├── reports/
│   ├── last_report.html
│   ├── latest.json
│   ├── pytest.json
│   ├── test_report.html
│   └── unit.html
├── scripts/
│   ├── diagnose_factors.py
│   ├── fetch_fundamentals.py
│   ├── fetch_news.py
│   ├── fetch_prices.py
│   ├── propose_portfolio.py
│   ├── rebuild_factors.py
│   ├── recompute_scores.py
│   ├── run_backtest.py
│   ├── test_env.py
│   ├── test_smart_decision.py
│   ├── test_technical_analysis.py
│   └── validate_enhancements.py
├── tests/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── test_agent_coordination.py
│   │   ├── test_all_agents.py
│   │   ├── test_backtest_engineer.py
│   │   ├── test_data_cleaner.py
│   │   ├── test_data_ingestor.py
│   │   ├── test_portfolio_manager.py
│   │   ├── test_risk_manager.py
│   │   └── test_signal_researcher.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── mock_responses.json
│   │   ├── sample_fundamentals.json
│   │   ├── sample_news.json
│   │   └── sample_prices.json
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_agent_pipeline.py
│   │   ├── test_api_integration.py
│   │   ├── test_end_to_end.py
│   │   └── test_orchestrator_flow.py
│   ├── logs/
│   ├── performance/
│   │   ├── __init__.py
│   │   ├── locustfile.py
│   │   ├── performance_report.py
│   │   ├── test_concurrent.py
│   │   ├── test_latency.py
│   │   └── test_throughput.py
│   ├── regression/
│   │   ├── snapshots/
│   │   ├── __init__.py
│   │   ├── test_api_contract.py
│   │   ├── test_portfolio_snapshot.py
│   │   └── test_scores_snapshot.py
│   ├── reports/
│   ├── security/
│   │   ├── __init__.py
│   │   ├── test_authentication.py
│   │   ├── test_authorization.py
│   │   ├── test_data_sanitization.py
│   │   ├── test_injection.py
│   │   └── test_xss.py
│   ├── stress/
│   │   ├── __init__.py
│   │   ├── test_data_overflow.py
│   │   ├── test_extreme_scenarios.py
│   │   ├── test_failure_recovery.py
│   │   ├── test_market_crash.py
│   │   └── test_resource_exhaustion.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── test_charts.py
│   │   ├── test_homepage.py
│   │   ├── test_navigation.py
│   │   ├── test_portfolio_page.py
│   │   ├── test_responsiveness.py
│   │   ├── test_simulator_page.py
│   │   └── test_stock_page.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── assertions.py
│   │   ├── data_factory.py
│   │   ├── fixtures.py
│   │   ├── helpers.py
│   │   └── mocks.py
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── test_backtest_accuracy.py
│   │   ├── test_data_consistency.py
│   │   ├── test_data_quality.py
│   │   ├── test_factor_ic.py
│   │   └── test_sentiment_accuracy.py
│   ├── __init__.py
│   ├── conftest.py
│   ├── paper_trading_simulator.py
│   ├── README.md
│   ├── run_visual_tests.sh
│   ├── test_cases_detailed.py
│   ├── test_runner.py
│   ├── TESTING_GUIDE.md
│   └── visual_dashboard.html
├── tools/
│   ├── db_backup.py
│   ├── export_csv.py
│   ├── generate_structure.py
│   ├── generate_tree.py
│   ├── print_file_tree.py
│   ├── run_tests_and_log.py
│   ├── update_snapshot.py
│   └── validate_config.py
├── __init__.py
├── requirements.txt
├── run.py
└── unit.html
```
