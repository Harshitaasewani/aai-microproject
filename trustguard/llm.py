"""Optional LLM layer. The pipeline is fully deterministic without it.

If ANTHROPIC_API_KEY is set and the `anthropic` package is installed, the orchestrator asks an LLM to
write the reviewer-facing explanation from the structured findings. The LLM never decides scores,
tiers or policy mappings — it only rewrites evidence the agents already produced into plain language.
"""
from __future__ import annotations

import json
import os

MODEL = os.environ.get("TRUSTGUARD_LLM_MODEL", "claude-sonnet-5-5")


def available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def explain(case_summary: dict, findings: list[dict], score: dict) -> str | None:
    if not available():
        return None
    try:
        import anthropic
        slim = [{k: f[k] for k in ("title", "detail", "severity", "policy_clause")} for f in findings[:8]]
        prompt = (
            "You are writing the explanation field of a marketplace trust & safety case report for a human "
            "reviewer. Use ONLY the facts below; do not invent numbers. 3 sentences max, neutral tone, no "
            "verdicts of guilt — describe what the evidence is consistent with.\n\n"
            f"Case: {json.dumps(case_summary, default=str)}\nScore: {json.dumps(score)}\nFindings: {json.dumps(slim)}")
        msg = anthropic.Anthropic().messages.create(model=MODEL, max_tokens=300,
                                                    messages=[{"role": "user", "content": prompt}])
        return msg.content[0].text.strip()
    except Exception:  # never let the optional layer break the pipeline
        return None
