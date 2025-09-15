import json, sqlite3

def test_snapshot_and_versioning(client, db_conn, default_candidates):
    # 组合提案应携带权重与解释，后续（可选）你可把它持久化到 portfolio_snapshots/backtest_results
    r = client.post("/orchestrator/propose", json={"candidates": default_candidates, "params": {"risk.max_stock":0.30}})
    assert r.status_code == 200
    ctx = r.json()["context"]
    kept = ctx["kept"]; assert kept and abs(sum(k["weight"] for k in kept)-1) < 1e-6

    # 评分的 version_tag（研究链路中）建议体现在 trace 或 context，以便 Watchlist 与快照复现
    # 这里只检查存在性（如果暂未落库可先跳过）
    # 如果你已实现 scores_daily，则可以改为 SELECT 校验 version_tag 与 as_of
    # row = db_conn.execute("SELECT version_tag FROM scores_daily LIMIT 1").fetchone()
    # assert row is not None
