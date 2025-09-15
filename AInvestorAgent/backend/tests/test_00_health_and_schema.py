def test_health(client, db_conn):
    # 里程碑0：能跑起来 + 基表存在
    r = client.get("/health")
    assert r.status_code == 200
    for table in ["symbols","prices_daily","fundamentals","news_raw","news_scores"]:
        row = db_conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'").fetchone()
        assert row is not None, f"missing table: {table}"
