"""
Local, offline mirror of the Guardrail / Verifier Skill (skills/guardrail_skill.md).

This is NOT the production CoCo skill — it's a small, dependency-free reimplementation used
so the Streamlit app can demo the full Analyst -> Citation -> Guardrail hand-off pattern
without a live Snowflake/Cortex connection. The verification logic mirrors the skill file
exactly; keep the two in sync if you change one.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Evidence:
    transaction_citations: list[dict] = field(default_factory=list)
    clause_citations: list[dict] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def insufficient(self) -> bool:
        return not self.transaction_citations or not self.clause_citations


@dataclass
class GuardrailResult:
    verdict: str          # CITED | DOWNGRADED | INSUFFICIENT_EVIDENCE
    message: str
    show_recommendation: bool


def verify(evidence: Evidence) -> GuardrailResult:
    """Mirrors skills/guardrail_skill.md verification logic."""
    if evidence.insufficient or evidence.confidence < 0.3:
        return GuardrailResult(
            verdict="INSUFFICIENT_EVIDENCE",
            message=(
                "Recommendation withheld: evidence does not meet the citation threshold "
                "(need at least one supporting transaction AND one matching regulatory "
                "clause). Routed to manual review instead of guessing."
            ),
            show_recommendation=False,
        )
    if evidence.confidence < 0.7:
        return GuardrailResult(
            verdict="DOWNGRADED",
            message=(
                "Answer shown with a caveat: evidence is present but confidence is "
                "moderate. Recommend a second reviewer before acting on this finding."
            ),
            show_recommendation=True,
        )
    return GuardrailResult(
        verdict="CITED",
        message="Every claim below is backed by at least one transaction and one regulatory clause citation.",
        show_recommendation=True,
    )
