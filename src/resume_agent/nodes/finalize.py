"""폴더 생성 · 파일 저장 · 지원 이력 기록."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from ..config import (LEDGER, PHOTO_SRC, RESUME_HTML_NAME, RESUME_PDF_NAME, RESUME_ROOT)

_CORP = re.compile(r"\(주\)|㈜|주식회사|\(유\)|㈜|Inc\.?|Co\.,?\s*Ltd\.?", re.I)
_DROP = re.compile(r'[\/:*?"<>|]')


def folder_name(company: str, job_title: str) -> str:
    """기존 관례에 맞춘다 — 예) 인피닉_AIAgentEngineer, 효성ITX_AIMLOps엔지니어"""
    co = _CORP.sub("", company or "").strip()
    co = re.sub(r"\([^)]*\)|\[[^\]]*\]", "", co)      # 숲(SOOP) → 숲 · 기존 폴더에 괄호가 없다
    co = _DROP.sub("", co).replace(" ", "")
    jt = job_title or ""
    jt = re.sub(r"\[[^\]]*\]|\([^)]*\)", "", jt)          # [급구] (3년이상) 같은 수식 제거
    jt = _DROP.sub("", jt)
    jt = re.sub(r"[\s·,\-–—_/]+", "", jt).strip()
    return f"{co or '미상'}_{jt or '직무미상'}"[:80]


def finalize(slots: dict, html_text: str, pdf_src: Path, candidate, jd,
             fit, gap, pages: int, trims: list[str], ingest_mode: str = "text") -> Path:
    out_dir = RESUME_ROOT / folder_name(jd.company, jd.job_title)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / RESUME_HTML_NAME).write_text(html_text, encoding="utf-8")
    if not (out_dir / "photo.jpg").exists() and PHOTO_SRC.exists():
        shutil.copyfile(PHOTO_SRC, out_dir / "photo.jpg")
    shutil.copyfile(pdf_src, out_dir / RESUME_PDF_NAME)

    # 폴더만 보고도 무슨 공고였는지 알 수 있게 남긴다
    from .jd_note import write_jd_note
    write_jd_note(out_dir, candidate, jd, fit, gap, ingest_mode, pages, trims)

    fit_score = getattr(fit, "score", 0)
    record = {
        "key": candidate.key,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": candidate.source,
        "url": candidate.url,                 # ★ 요청하신 산출물 — 공고 URL
        "company": jd.company,
        "job_title": jd.job_title,
        "folder": str(out_dir),
        "fit_score": fit_score,
        "pages": pages,
        "trims": trims,
        "deadline": jd.deadline or candidate.due or "",
        "status": "생성",
    }
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return out_dir


def record_skipped(candidate, jd, fit_score: int, reason: str) -> None:
    """게이트에서 걸러진 공고도 URL 은 남긴다 — 중복 수집 방지 + 나중에 눈으로 확인."""
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "key": candidate.key,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": candidate.source,
            "url": candidate.url,
            "company": (jd.company if jd else candidate.company),
            "job_title": (jd.job_title if jd else candidate.title),
            "fit_score": fit_score,
            "status": "제외",
            "reason": reason,
        }, ensure_ascii=False) + "\n")
