from __future__ import annotations
import re

_POS = {"beat", "surge", "growth", "upgrade", "strong", "record", "positive", "gain", "outperform", "buy"}
_NEG = {"miss", "fall", "downgrade", "lawsuit", "fraud", "negative", "loss", "recall", "layoff", "sell"}

def classify_polarity(title: str, summary: str = "") -> float:
    """
    轻量关键词投票：返回情绪[-1,1]。与架构文档一致，后续可换LLM或词典。
    """
    text = f"{title} {summary}".lower()
    pos = sum(1 for w in _POS if re.search(rf"\\b{re.escape(w)}\\b", text))
    neg = sum(1 for w in _NEG if re.search(rf"\\b{re.escape(w)}\\b", text))
    if pos == neg == 0:
        return 0.0
    score = (pos - neg) / max(pos + neg, 1)
    return max(-1.0, min(1.0, score))
