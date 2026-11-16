"""Shared data contracts. Every detection agent returns the same AgentResult shape, which is what
lets the orchestrator, compliance mapper and scorer treat agents as plug-in modules."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Flag:
    flag_type: str            # machine key, e.g. "volume_spike" -> used by the compliance mapper
    title: str                # short human label
    detail: str               # one-line explanation with the numbers
    severity: str = "medium"  # low | medium | high | critical
    evidence: list[Any] = field(default_factory=list)  # review ids, reviewer ids, image files, events...

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AgentResult:
    agent: str
    score: float              # 0 = no risk signal, 1 = maximal risk signal
    confidence: float         # 0..1, how much data / how reliable the signal is
    flags: list[Flag] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["score"] = round(self.score, 3)
        d["confidence"] = round(self.confidence, 3)
        return d


@dataclass
class CaseData:
    """Output of the Ingestion Agent: one product's analysis-ready data plus marketplace context."""
    product: dict
    seller: dict
    reviews: Any               # DataFrame, timestamps normalized to UTC, joined with reviewer metadata
    price_history: Any         # DataFrame
    seller_events: Any         # DataFrame
    certifications: Any        # DataFrame for this product
    market: Any                # MarketData (all tables) for baselines and cross-listing checks
    as_of: Any                 # pandas Timestamp (UTC)
    summary: dict = field(default_factory=dict)
    data_quality: list[str] = field(default_factory=list)
