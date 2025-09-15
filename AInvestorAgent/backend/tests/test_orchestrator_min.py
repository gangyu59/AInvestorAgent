from backend.orchestrator.pipeline import run_pipeline

def test_pipeline_mock_aapl():
    res = run_pipeline("AAPL", {"mock": True})
    assert res["trace"] and res["trace"][0]["agent"] == "data_ingestor"
    assert res["context"].get("score") is not None
    f = res["context"].get("factors", {})
    for k in ["value","quality","momentum","sentiment"]:
        assert k in f
