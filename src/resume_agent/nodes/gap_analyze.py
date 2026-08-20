"""갭 분석 — JD 요건 × 프로필 근거. 정직 표기와 점선칩의 입력이 된다."""
from __future__ import annotations

import io

import yaml

from ..config import PROFILE_DIR, profile_text
from ..llm import MODEL_WRITE, generate_json
from ..schemas import GapAnalysis, JD

PROMPT = """지원자의 보유 역량과 미경험 항목이다.

{career_facts}

[보유 — 이 목록에 있는 것만 '충족' 으로 인정한다]
{have}

[미경험 — 이 목록에 있으면 무조건 '미경험']
{not_yet}

[프로젝트에서 실제로 한 일]
{deeds}

--- 채용 공고 ---
회사: {company} / 직무: {title}
담당업무:
{resp}
자격요건(필수):
{req}
우대사항:
{pref}

할 일:
1. 자격요건과 우대사항을 **하나씩** 판정해라 — 충족 / 부분충족 / 미경험.
   - 보유 목록이나 '실제로 한 일' 에 직접 근거가 있으면 충족
   - 비슷하지만 규모·형태가 다르면 부분충족 (근거를 적어라)
   - 근거가 없으면 미경험. **추측으로 충족을 주지 마라.**
2. not_experienced 에는 **필수 자격요건 중 미경험인 것**만 담아라 (우대사항은 제외).
3. top_priorities 에는 담당업무를 중요한 순서대로 4개 정리해라 — 이력서 핵심역량 4줄의 순서가 된다."""


def _load():
    sk = yaml.safe_load(io.open(PROFILE_DIR / "skills.yaml", encoding="utf-8"))
    pj = yaml.safe_load(io.open(PROFILE_DIR / "projects.yaml", encoding="utf-8"))
    have = [c["name"] for g in sk["have"].values() for c in g["chips"]]
    not_yet = [f'{n["name"]} (대신: {n.get("alt","")})' for n in sk["not_yet"]]
    deeds = []
    for b in pj["main_project"]["blocks"]:
        for bl in b["bullets"]:
            deeds.append(" ".join(bl["text"].split()))
    for bl in pj["career"]["bullets"]:
        deeds.append(" ".join(bl["text"].split()))
    for s in pj["side_projects"]:
        deeds.append(" ".join(s["text"].split()))
    return have, not_yet, deeds


def _fmt(items: list[str], n: int = 15) -> str:
    return "\n".join(f"- {x}" for x in items[:n]) or "- (없음)"


def gap_analyze(jd: JD) -> GapAnalysis:
    have, not_yet, deeds = _load()
    out = generate_json(
        PROMPT.format(career_facts=profile_text("career_facts.md").strip(),
                      have=_fmt(have, 40), not_yet=_fmt(not_yet, 20), deeds=_fmt(deeds, 30),
                      company=jd.company, title=jd.job_title,
                      resp=_fmt(jd.responsibilities), req=_fmt(jd.requirements),
                      pref=_fmt(jd.preferred)),
        GapAnalysis, model=MODEL_WRITE, temperature=0.1)
    if isinstance(out, GapAnalysis):
        return out
    try:
        return GapAnalysis.model_validate_json(out)
    except Exception:  # noqa: BLE001
        return GapAnalysis()
