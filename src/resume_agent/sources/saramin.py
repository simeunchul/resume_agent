"""사람인 오픈API. SARAMIN_ACCESS_KEY 가 .env 에 있으면 자동으로 켜진다.

⚠️ 키가 없어 응답 구조를 실측하지 못했다. 공식 문서 기준으로 짜고 방어적으로 읽는다.
   키를 넣고 처음 돌릴 때 scripts/probe_saramin.py 로 실제 구조를 확인할 것.
"""
from __future__ import annotations

import os
import urllib.parse

from .base import JobCandidate, http_json

API = ("https://oapi.saramin.co.kr/job-search"
       "?access-key={key}&keywords={q}&count={n}&sort=pd&fields=posting-date")


def _dig(d, *path, default=""):
    """사람인 응답은 중첩이 깊고 필드가 자주 빠진다."""
    cur = d
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    if isinstance(cur, dict):
        cur = cur.get("name", default)
    return cur if cur not in (None, {}) else default


def collect(keywords: list[str], count: int = 20) -> list[JobCandidate]:
    key = os.getenv("SARAMIN_ACCESS_KEY", "").strip()
    if not key:
        return []                                  # 키 없으면 조용히 건너뛴다
    out: list[JobCandidate] = []
    for kw in keywords:
        data = http_json(API.format(key=key, q=urllib.parse.quote(kw), n=count))
        if not data:
            continue
        jobs = (data.get("jobs") or {}).get("job") or []
        if isinstance(jobs, dict):
            jobs = [jobs]
        for j in jobs:
            jid = str(j.get("id") or "")
            url = j.get("url") or ""
            if not jid or not url:
                continue
            out.append(JobCandidate(
                source="saramin",
                source_id=jid,
                url=url,
                title=_dig(j, "position", "title"),
                company=_dig(j, "company", "detail", "name"),
                job_category=_dig(j, "position", "job-mid-code"),
                due=str(j.get("expiration-date") or ""),
                employment_type=_dig(j, "position", "job-type"),
                location=_dig(j, "position", "location"),
            ))
    return out
