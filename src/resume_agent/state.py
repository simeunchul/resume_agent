"""LangGraph 상태."""
from __future__ import annotations

from typing import Any, TypedDict


class JobState(TypedDict, total=False):
    """공고 한 건이 그래프를 통과하는 동안의 상태."""
    candidate: Any          # JobCandidate
    jd: Any                 # JD
    ingest_mode: str        # text | image
    fit: Any                # FitScore
    gap: Any                # GapAnalysis
    slots: dict
    violations: list[str]
    fact_round: int
    html_path: str
    pdf_path: str
    pages: int
    trim_round: int
    trims: list[str]
    outcome: str            # 생성 | 제외 | 실패
    reason: str
    out_dir: str
