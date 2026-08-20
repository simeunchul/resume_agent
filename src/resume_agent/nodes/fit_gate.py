"""적합도 게이트 — 이력서를 만들 가치가 있는 공고인지 판정.

사람이 개입하지 않는 완전 자동 모드라서, 이 게이트가 없으면
관련 없는 공고까지 폴더가 쌓인다.
"""
from __future__ import annotations

import re

from ..config import FIT_THRESHOLD, MIN_YEARS_BLOCK, profile_text
from ..llm import MODEL_READ, generate_json
from ..schemas import FitScore, JD

# 지원자 배경은 코드에 두지 않는다 — profile/summary.md 가 단일 출처다.
_summary: str | None = None


def profile_summary() -> str:
    global _summary
    if _summary is None:
        _summary = profile_text("summary.md").strip()
    return _summary


PROMPT = """{profile}

--- 채용 공고 ---
회사: {company}
직무: {title}
고용형태: {emp} | 경력요건: {exp}
담당업무:
{resp}
자격요건:
{req}
우대사항:
{pref}

이 공고가 위 지원자에게 지원할 가치가 있는지 0-100 으로 평가해라.

기준:
- AI 에이전트 / LLM / RAG / MLOps / 데이터 엔지니어링 / 데이터 분석 직무일수록 높다.
- 직무명이 아니라 담당업무·자격요건의 **실제 내용**으로 판단해라.
- 교육생·연수생·부트캠프 모집, 영업·마케팅·디자인·HW/임베디드 전담은 20점 이하.

경력 연차 — **판정하지 말고 숫자만 뽑아라**:
- 지원자의 정규 경력은 위 배경에 적힌 것이 전부다. 프로젝트 참여 기간을 더해 연차를 부풀리지 마라.
- `min_years_required` 에 공고가 요구하는 경력의 **하한**을 숫자로만 담는다:
  · "경력 3~5년" → **3**      · "3년 이상" → **3**      · "5년 이상" → **5**
  · "경력 2~7년" → **2**      · "2년 이상" → **2**      · "1~3년"   → **1**
  · "신입", "경력무관", "신입·경력" → **0**
  · 공고 어디에도 연차 언급이 없으면 → **-1**
- 구간이 여러 곳에 나오면 **가장 낮은 하한**을 쓴다 (우대사항의 연차는 무시, 필수만).
- ★ **연차 미달을 blockers 에 넣지 마라. 합격/불합격은 코드가 정한다.**
  연차가 부족하다는 사실은 reason 에만 한 줄로 적어라.
- 감점도 하지 마라. 점수는 **직무 적합도만** 보고 매긴다 (연차는 코드가 따로 본다).

- blockers 에 넣을 결격 사유 (연차 제외):
  · '팀장·리드·시니어·매니저' 급으로 명시된 경우
  · 직무가 완전히 다른 분야인 경우 (예: 임베디드 펌웨어 전담, 반도체 공정)
  · 교육생·연수생·부트캠프·인턴 모집인 경우
  · 법정 필수 자격증·면허가 요건인 경우 (예: 의사, 변호사, 세무사)
  · 석사·박사 학위가 **필수**로 명시된 경우 (우대는 해당 없음)"""


def _fmt(items: list[str], n: int = 12) -> str:
    return "\n".join(f"- {x}" for x in items[:n]) or "- (없음)"


def fit_gate(jd: JD) -> FitScore:
    out = generate_json(
        PROMPT.format(profile=profile_summary(), company=jd.company, title=jd.job_title,
                      emp=jd.employment_type or "-", exp=jd.experience_level or "-",
                      resp=_fmt(jd.responsibilities), req=_fmt(jd.requirements),
                      pref=_fmt(jd.preferred)),
        FitScore, model=MODEL_READ)
    if isinstance(out, FitScore):
        return out
    try:
        return FitScore.model_validate_json(out)
    except Exception:  # noqa: BLE001
        return FitScore(score=0, reason="적합도 판정 실패", matched=[], blockers=["parse error"])


# LLM 이 지시를 어기고 연차 얘기를 blockers 에 넣는 경우가 있어 코드에서 걷어낸다.
# 연차 판정은 min_years_required 숫자 하나로만 한다 — 판정을 두 곳에서 하면 어긋난다.
_CAREER_BLOCKER = re.compile(r"경력|연차|년\s*이상|년차|실무\s*경험")


def evaluate(fit: FitScore) -> tuple[bool, str]:
    """게이트 판정. 통과 여부와 사유를 함께 돌려준다.

    연차는 LLM 이 아니라 여기서 판정한다 — '하한 N년 이상이면 결격'은 숫자 비교라
    LLM 에게 맡길 이유가 없고, 맡겼더니 하한 1~2년 공고까지 결격 처리했다 (2026-08-20).
    """
    if fit.min_years_required >= MIN_YEARS_BLOCK:
        return False, (f"요구 경력 하한 {fit.min_years_required}년 "
                       f"(본인 정규 경력 10개월, 기준 {MIN_YEARS_BLOCK}년)")

    others = [b for b in fit.blockers if not _CAREER_BLOCKER.search(b)]
    if others:
        return False, "; ".join(others)

    if fit.score < FIT_THRESHOLD:
        return False, f"적합도 {fit.score} (기준 {FIT_THRESHOLD})"
    return True, ""


def passes(fit: FitScore) -> bool:
    return evaluate(fit)[0]
