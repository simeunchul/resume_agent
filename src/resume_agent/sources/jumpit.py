"""점핏 — positions API. 하이라이트 <span> 태그가 섞여 오므로 반드시 벗겨낸다."""
from __future__ import annotations

import urllib.parse

from .base import JobCandidate, http_json, strip_tags

SEARCH = "https://api.jumpit.co.kr/api/positions?sort=reg_dt&highlight=false&page={p}&keyword={q}"
JOB_URL = "https://jumpit.saramin.co.kr/position/{id}"


def collect(keywords: list[str], pages: int = 1) -> list[JobCandidate]:
    out: list[JobCandidate] = []
    for kw in keywords:
        for p in range(1, pages + 1):
            data = http_json(SEARCH.format(p=p, q=urllib.parse.quote(kw)))
            if not data:
                continue
            for it in (data.get("result") or {}).get("positions") or []:
                jid = str(it.get("id"))
                out.append(
                    JobCandidate(
                        source="jumpit",
                        source_id=jid,
                        url=JOB_URL.format(id=jid),
                        title=strip_tags(it.get("title")),
                        company=strip_tags(it.get("companyName")),
                        job_category=strip_tags(it.get("jobCategory")),
                        tech_stacks=[strip_tags(t) for t in (it.get("techStacks") or [])],
                        due=it.get("closedAt"),
                        location=", ".join(it.get("locations") or []),
                    )
                )
    return out
