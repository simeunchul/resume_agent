"""원티드 — chaos search API. 실측: positions.data 에 필요한 필드가 모두 있다."""
from __future__ import annotations

import urllib.parse

from .base import JobCandidate, http_json

SEARCH = "https://www.wanted.co.kr/api/chaos/search/v1/results?query={q}&tab=position"
JOB_URL = "https://www.wanted.co.kr/wd/{id}"


def collect(keywords: list[str]) -> list[JobCandidate]:
    out: list[JobCandidate] = []
    for kw in keywords:
        data = http_json(SEARCH.format(q=urllib.parse.quote(kw)))
        if not data:
            continue
        for it in (data.get("positions") or {}).get("data") or []:
            company = it.get("company") or {}
            addr = it.get("address") or {}
            jid = str(it.get("id"))
            # category_tag 은 {"parent_id":518,"id":665} 처럼 ID 만 온다 (이름 없음)
            ct = it.get("category_tag")
            cat = f"{ct.get('parent_id')}/{ct.get('id')}" if isinstance(ct, dict) else str(ct or "")
            out.append(
                JobCandidate(
                    source="wanted",
                    source_id=jid,
                    url=JOB_URL.format(id=jid),
                    title=it.get("position") or "",
                    company=company.get("name", "") if isinstance(company, dict) else str(company),
                    job_category=cat,
                    due=it.get("due_time"),
                    employment_type=it.get("employment_type") or "",
                    location=addr.get("location", "") if isinstance(addr, dict) else "",
                )
            )
    return out
