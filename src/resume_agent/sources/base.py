"""공고 후보 공통 자료구조 + HTTP 헬퍼."""
from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict

from ..config import USER_AGENT, RELEVANT_TERMS, EXCLUDE_TERMS

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

_TAG = re.compile(r"<[^>]+>")


def strip_tags(s: str | None) -> str:
    """점핏 응답에 섞여 오는 <span> 하이라이트 태그 제거."""
    if not s:
        return ""
    return _TAG.sub("", s).strip()


def http_get(url: str, headers: dict | None = None, timeout: int = 20) -> tuple[int | None, bytes]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:1000]
    except Exception as e:  # noqa: BLE001 - 소스 하나가 죽어도 수집은 계속돼야 한다
        return None, f"{type(e).__name__}: {e}".encode()


def http_json(url: str, headers: dict | None = None, timeout: int = 20) -> dict | None:
    st, body = http_get(url, headers, timeout)
    if st != 200:
        return None
    try:
        return json.loads(body)
    except Exception:  # noqa: BLE001
        return None


@dataclass
class JobCandidate:
    source: str                 # wanted | jumpit | jobkorea | saramin
    source_id: str
    url: str
    title: str
    company: str
    job_category: str = ""
    tech_stacks: list[str] = field(default_factory=list)
    due: str | None = None
    employment_type: str = ""
    location: str = ""

    @property
    def key(self) -> str:
        return f"{self.source}:{self.source_id}"

    def haystack(self) -> str:
        parts = [str(self.title or ""), str(self.job_category or "")]
        parts += [str(t) for t in (self.tech_stacks or [])]
        return " ".join(parts).lower()

    def is_relevant(self) -> bool:
        """규칙 기반 1차 필터. 느슨하게 — 최종 판단은 fit_gate 가 한다."""
        hay = self.haystack()
        if any(x in hay for x in EXCLUDE_TERMS):
            return False
        return any(x in hay for x in RELEVANT_TERMS)

    def to_dict(self) -> dict:
        return asdict(self)
