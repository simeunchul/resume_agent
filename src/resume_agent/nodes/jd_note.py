"""공고 정보를 회사 폴더에 남긴다.

폴더에 이력서만 있으면 나중에 "이게 무슨 공고였지" 를 알 수 없다.
지원 후 면접 준비 때 다시 찾아야 하는데 공고는 마감되면 내려간다.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

FILENAME = "공고.md"


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {x}" for x in items) if items else "- (공고에 명시 없음)"


def write_jd_note(out_dir: Path, candidate, jd, fit, gap, ingest_mode: str,
                  pages: int, trims: list[str]) -> Path:
    L: list[str] = []
    L += [f"# {jd.company} — {jd.job_title}", ""]
    L += [f"**공고 URL** · <{candidate.url}>", ""]
    L += ["| | |", "|---|---|"]
    L += [f"| 수집 | {candidate.source} · {datetime.now():%Y-%m-%d %H:%M} |"]
    L += [f"| 마감 | {jd.deadline or candidate.due or '상시/미상'} |"]
    L += [f"| 고용형태 | {jd.employment_type or '-'} |"]
    L += [f"| 경력요건 | {jd.experience_level or '-'} |"]
    L += [f"| 근무지 | {jd.location or '-'} |"]
    if jd.tech_stack:
        L += [f"| 기술스택 | {', '.join(jd.tech_stack)} |"]
    L += [f"| 적합도 | **{fit.score}** |"]
    L += ["", f"> {fit.reason}", ""]
    if fit.blockers:
        L += ["**주의**", _bullets(fit.blockers), ""]

    L += ["---", "", "## 담당업무", _bullets(jd.responsibilities), ""]
    L += ["## 자격요건 (필수)", _bullets(jd.requirements), ""]
    L += ["## 우대사항", _bullets(jd.preferred), ""]

    if gap and gap.items:
        L += ["---", "", "## 요건별 판정", "",
              "| 요건 | 판정 | 근거 |", "|---|---|---|"]
        for it in gap.items:
            req = (it.requirement or "").replace("|", "/")[:70]
            ev = (it.evidence or "").replace("|", "/")[:70]
            L += [f"| {req} | {it.verdict} | {ev} |"]
        L += [""]
    if gap and gap.not_experienced:
        L += ["**필수요건 중 미경험** — 정직 표기와 점선칩에 반영됨",
              _bullets(gap.not_experienced), ""]

    L += ["---", "", "## 생성 정보",
          f"- 공고 읽기: {'이미지(VLM 판독)' if ingest_mode == 'image' else '텍스트'}",
          f"- 이력서: {pages}페이지"]
    if trims:
        L += [f"- 분량 조정: {' → '.join(trims)}"]
    L += ["", "## 지원 기록", "", "- [ ] 지원함 (날짜: )", "- [ ] 서류 결과 (          )", ""]

    p = out_dir / FILENAME
    p.write_text("\n".join(L), encoding="utf-8")
    return p
