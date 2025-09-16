# backend/agents/registry.py
from .news_sentiment import NewsSentimentAgent
from .macro import MacroAgent
from .earnings import EarningsAgent
from .technical import TechnicalAgent
from .value import ValueAgent
from .quant import QuantAgent
from .macro_strategy import MacroStrategyAgent
from .chair import ChairAgent
from .execution import ExecutionAgent

REGISTRY = {
    "news": NewsSentimentAgent(),
    "macro": MacroAgent(),
    "earnings": EarningsAgent(),
    "technical": TechnicalAgent(),
    "value": ValueAgent(),
    "quant": QuantAgent(),
    "macro_strategy": MacroStrategyAgent(),
    "chair": ChairAgent(),
    "execution": ExecutionAgent(),
}

ORDER = ["news","macro","earnings","technical","value","quant","macro_strategy","chair","execution"]
