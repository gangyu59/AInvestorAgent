import importlib

def test_news_sentiment_agent_mock_outputs():
    ba = importlib.import_module("backend.agents.base_agent")
    news = importlib.import_module("backend.agents.news_sentiment")

    agent = news.NewsSentimentAgent()
    ctx = ba.ResearchContext(symbol="MSFT")
    out = agent.run(ctx, mock=True)

    assert "sentiment" in out.factors
    s = out.factors["sentiment"]
    assert 0.0 <= s <= 1.0
    top = out.signals.get("news", {}).get("top", [])
    assert isinstance(top, list)
    assert len(top) >= 1
