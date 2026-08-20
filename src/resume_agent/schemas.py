"""LLM 구조화 출력 스키마."""
from __future__ import annotations

from pydantic import BaseModel, Field


class JD(BaseModel):
    """채용 공고에서 뽑아낼 구조."""
    company: str = Field(description="회사명. (주)·㈜ 같은 법인격 표기는 뺀다")
    job_title: str = Field(description="직무명")
    responsibilities: list[str] = Field(default_factory=list, description="담당업무·주요업무")
    requirements: list[str] = Field(default_factory=list, description="자격요건·필수요건")
    preferred: list[str] = Field(default_factory=list, description="우대사항")
    tech_stack: list[str] = Field(default_factory=list, description="기술 스택")
    employment_type: str = Field(default="", description="정규직/계약직/인턴 등")
    deadline: str = Field(default="", description="마감일. 상시채용이면 '상시'")
    location: str = Field(default="", description="근무지")
    experience_level: str = Field(default="", description="신입/경력 n년 등")


class FitScore(BaseModel):
    """적합도 게이트 — 이력서를 만들 가치가 있는 공고인가."""
    score: int = Field(description="0-100. 지원자의 경력(AI 에이전트·LLM·RAG·MLOps·데이터 엔지니어링)과의 적합도")
    reason: str = Field(description="점수 근거 한두 문장")
    matched: list[str] = Field(default_factory=list, description="맞는 요건")
    blockers: list[str] = Field(
        default_factory=list,
        description="치명적 결격 사유. ★경력 연차 관련은 절대 넣지 마라 — 코드가 따로 판정한다")
    min_years_required: int = Field(
        default=-1,
        description=("공고가 요구하는 경력의 **하한** 연차를 숫자로만 추출. 판정하지 말고 숫자만. "
                     "'3~5년'→3, '2년 이상'→2, '1~3년'→1, '신입'·'경력무관'→0, 연차 언급이 전혀 없으면 -1"))


class GapItem(BaseModel):
    requirement: str = Field(description="JD 의 요건 원문")
    verdict: str = Field(description="충족 / 부분충족 / 미경험 중 하나")
    evidence: str = Field(default="", description="충족·부분충족이면 근거가 되는 프로필 사실")


class GapAnalysis(BaseModel):
    items: list[GapItem] = Field(default_factory=list)
    not_experienced: list[str] = Field(default_factory=list, description="점선칩·정직표기에 쓸 미경험 항목")
    top_priorities: list[str] = Field(default_factory=list, description="JD 담당업무 우선순위 (핵심역량 4개 순서)")
