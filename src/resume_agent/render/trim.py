"""분량 초과 시 내용을 덜어낸다.

★ zoom 은 절대 건드리지 않는다. 정해진 순서로 내용만 뺀다:
   ① 기타 프로젝트 → ② 프로젝트 블록의 bullet(뒤에서부터) → ③ 핵심역량 문장 축약
"""
from __future__ import annotations

import copy
import re


def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def trim_once(slots: dict, round_no: int) -> tuple[dict, str]:
    """한 단계만 덜어내고, 무엇을 뺐는지 함께 돌려준다."""
    s = copy.deepcopy(slots)

    # ① 기타 프로젝트 — 뒤에서부터 하나씩
    if s.get("side_projects"):
        dropped = s["side_projects"].pop()
        return s, f"기타 프로젝트 제거: {dropped.get('title', '?')}"

    # ② 프로젝트 블록의 bullet — bullet 이 가장 많은 블록에서 뒤에서부터
    blocks = s.get("blocks") or []
    cand = [(i, b) for i, b in enumerate(blocks) if len(b.get("bullets") or []) > 2]
    if cand:
        i, b = max(cand, key=lambda x: len(x[1]["bullets"]))
        dropped = b["bullets"].pop()
        return s, f"블록 '{b.get('title','?')}' bullet 1개 제거 ({_strip_tags(dropped)[:40]}…)"

    # ③ 핵심역량 문장 축약 — 가장 긴 것의 뒷문장을 자른다
    core = s.get("core") or []
    if core:
        i = max(range(len(core)), key=lambda k: len(core[k].get("body", "")))
        body = core[i]["body"]
        parts = re.split(r"(?<=[.。])\s+|(?<=함)\s+(?=[가-힣])", body)
        if len(parts) > 1:
            core[i]["body"] = " ".join(parts[:-1]).rstrip()
            return s, f"핵심역량 {i+1}번 문장 축약"
        if len(body) > 120:
            core[i]["body"] = body[:110].rstrip() + "…"
            return s, f"핵심역량 {i+1}번 절단"

    return s, "더 뺄 것이 없음"
