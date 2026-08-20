"""공고 수집 — 소스별로 모아 중복 제거하고 1차 필터를 건다."""
from __future__ import annotations

import json
from pathlib import Path

from ..config import LEDGER, SEARCH_KEYWORDS
from . import jumpit, saramin, wanted
from .base import JobCandidate


def _seen_keys() -> set[str]:
    """이미 처리한 공고 키. 같은 공고를 두 번 만들지 않기 위한 대장."""
    if not Path(LEDGER).exists():
        return set()
    keys = set()
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                keys.add(json.loads(line)["key"])
            except Exception:  # noqa: BLE001
                continue
    return keys


def collect_all(keywords: list[str] | None = None, use_jobkorea: bool = False) -> dict:
    """수집 → 중복 제거 → 1차 필터. 각 단계 건수를 함께 돌려준다."""
    kws = keywords or SEARCH_KEYWORDS
    raw: list[JobCandidate] = []
    per_source: dict[str, int] = {}

    for name, fn in (("wanted", lambda: wanted.collect(kws)),
                     ("jumpit", lambda: jumpit.collect(kws)),
                     ("saramin", lambda: saramin.collect(kws))):   # 키 없으면 0건
        try:
            got = fn()
        except Exception as e:  # noqa: BLE001 - 소스 하나가 죽어도 나머지는 계속
            print(f"  [warn] {name} 수집 실패: {type(e).__name__}: {e}")
            got = []
        per_source[name] = len(got)
        raw.extend(got)

    if use_jobkorea:
        from . import jobkorea
        try:
            got = jobkorea.collect(kws)
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] jobkorea 수집 실패: {type(e).__name__}: {e}")
            got = []
        per_source["jobkorea"] = len(got)
        raw.extend(got)

    # 소스 내/간 중복 제거 (같은 공고가 키워드 여러 개에 걸린다)
    uniq: dict[str, JobCandidate] = {}
    for c in raw:
        uniq.setdefault(c.key, c)

    already = _seen_keys()
    fresh = [c for c in uniq.values() if c.key not in already]
    relevant = [c for c in fresh if c.is_relevant()]

    return {
        "per_source": per_source,
        "raw": len(raw),
        "unique": len(uniq),
        "fresh": len(fresh),
        "relevant": relevant,
    }
