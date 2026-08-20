"""이력서 슬롯 생성.

★ 설계의 핵심 — LLM 에게 HTML 을 쓰게 하지 않는다. 그리고 **수치가 든 문장도 쓰게 하지 않는다.**

  · 프로젝트 bullet 은 projects.yaml 의 풀에서 **인덱스로 고르기만** 한다 → 원문 그대로 복사됨
  · 스킬 칩도 skills.yaml 의 이름 중에서만 고른다
  · LLM 이 자유롭게 쓰는 것은 한 줄 소개 · 핵심역량 4줄 · 블록 제목 · 그룹명 · 정직 표기뿐

이렇게 하면 환각이 들어올 수 있는 표면이 좁아지고, 남은 표면은 fact_guard 가 막는다.
"""
from __future__ import annotations

import io

import yaml
from pydantic import BaseModel, Field

from ..config import PROFILE_DIR
from ..llm import MODEL_WRITE, generate_json
from ..schemas import GapAnalysis, JD


# ── LLM 출력 스키마 ────────────────────────────────────────────────────
class CoreItem(BaseModel):
    title: str = Field(description="핵심역량 제목. JD 담당업무 언어로")
    body: str = Field(description="무엇을 했고 결과가 무엇인지. <b> 강조 허용")


class BlockChoice(BaseModel):
    block_id: str = Field(description="위 bullet 풀에 제시된 블록 id 중 하나 (대괄호 안의 값)")
    title: str = Field(description="이 블록을 JD 언어로 다시 쓴 제목")
    bullet_indices: list[int] = Field(description="이 블록에서 쓸 bullet 의 인덱스. 2~4개")


class ComposeOut(BaseModel):
    tagline: str = Field(description="한 줄 소개. '{JD가 요구하는 일}을 {어떤 조건에서} 해 온 개발자' 공식")
    core: list[CoreItem] = Field(description="핵심역량 정확히 4개. JD 담당업무 순서대로")
    blocks: list[BlockChoice] = Field(description="프로젝트 블록 정확히 3개")
    emphasis: str = Field(default="", description="소속 뒤 괄호에 넣을 강조점. 없으면 빈 문자열")
    role_boundary_led: str = Field(description="'본인 주도' 뒤에 올 구간. JD 에 맞게")
    skill_group1_label: str = Field(description="스킬 1그룹 이름. JD 핵심 영역 언어로")
    skill_group1_chips: list[str] = Field(description="1그룹 칩. 보유 목록의 이름만")
    skill_group2_label: str = Field(description="스킬 2그룹 이름")
    skill_group2_chips: list[str] = Field(description="2그룹 칩. 보유 목록의 이름만")
    not_yet_chips: list[str] = Field(description="점선칩. 미경험 목록의 이름만. 3~5개")
    honesty_note: str = Field(description="정직 표기 note")
    career_first: bool = Field(default=False, description="경력(서버팀)을 프로젝트보다 위로 올릴지")
    side_project_ids: list[str] = Field(default_factory=list, description="쓸 기타 프로젝트 id. 위 '기타 프로젝트' 목록의 id 만")


PROMPT = """너는 지원자의 이력서를 이 공고에 맞춰 다시 쓰는 일을 한다.
**같은 사실을 그 회사 JD 언어로 다시 번역하는 것이 전부다.** 없는 경험을 만들지 마라.

{rules}

═══ 채용 공고 ═══
회사: {company} / 직무: {job_title}
담당업무:
{resp}
자격요건(필수):
{req}
우대사항:
{pref}

═══ 갭 분석 결과 ═══
JD 담당업무 우선순위: {priorities}
필수요건 중 미경험: {not_exp}

═══ 고를 수 있는 프로젝트 bullet (인덱스로 지정한다) ═══
{pool}

═══ 고를 수 있는 스킬 칩 (이 이름 그대로만 쓴다) ═══
보유: {have}
미경험(점선칩): {not_yet}

═══ 기타 프로젝트 ═══
{sides}

═══ 반드시 지킬 것 ═══
1. **핵심역량 4개는 JD 담당업무 우선순위 순서대로** 배치한다.
2. 핵심역량 body 에 쓸 수 있는 수치는 아래 목록에 있는 것뿐이다. 이 목록 밖의 숫자를 쓰면 거부된다:
{allowed_numbers}
3. bullet 은 **인덱스로만** 고른다. 문장을 새로 쓰거나 고치지 마라.
4. "혼자 / 단독" 은 **운영 감사 에이전트에만** 붙인다. 추천 모델 아키텍처·학습은 팀 공동이다.
5. 정직 표기 note 에는 세 가지가 다 들어가야 한다:
   ① 필수요건 중 미경험 항목 + 왜 그렇게 됐는지 + 대신 무엇을 했는지
   ② 역할 경계 (팀 공동 / 본인 주도)
   ③ 참여 형태 — 위 작성 규칙의 '경력 연차' 항목에 적힌 사실(정규 경력 기간, 참여 형태)을
      그대로 밝힌다. 기간을 합산하거나 바꿔 쓰지 마라
   미경험을 먼저 인정하고 "대신 무엇을 했는지" 로 닫는 구조로 쓴다.
6. Elastic Stack · 검색 · 서버 운영 중심 직무면 career_first 를 true 로 한다.
7. 강조는 <b></b> 만 쓴다. 다른 HTML 태그는 쓰지 마라.
{extra}"""


def _load():
    return (yaml.safe_load(io.open(PROFILE_DIR / "projects.yaml", encoding="utf-8")),
            yaml.safe_load(io.open(PROFILE_DIR / "skills.yaml", encoding="utf-8")),
            yaml.safe_load(io.open(PROFILE_DIR / "facts.yaml", encoding="utf-8")),
            io.open(PROFILE_DIR / "rules.md", encoding="utf-8").read())


def _pool_text(pj: dict) -> str:
    lines = []
    for b in pj["main_project"]["blocks"]:
        lines.append(f"\n[{b['id']}] {b['title']} ({b['period']}, {b['scope']})")
        for i, bl in enumerate(b["bullets"]):
            tags = ",".join(bl.get("tags") or [])
            lines.append(f"  {i}. ({tags}) {' '.join(bl['text'].split())}")
    return "\n".join(lines)


def _fmt(items: list[str], n: int = 15) -> str:
    return "\n".join(f"- {x}" for x in items[:n]) or "- (없음)"


def compose(jd: JD, gap: GapAnalysis, violations: list[str] | None = None) -> dict:
    """슬롯 dict 를 만든다. violations 가 있으면 그것을 고치라고 지시하며 다시 쓴다."""
    pj, sk, fx, rules = _load()

    allowed = sorted({str(n) for f in fx.get("facts") or [] for n in (f.get("numbers") or [])})
    have = [c["name"] for g in sk["have"].values() for c in g["chips"]]
    not_yet = [n["name"] for n in sk["not_yet"]]
    sides = [f"{s['id']}: {s['title']} — {' '.join(s['text'].split())[:90]}" for s in pj["side_projects"]]

    extra = ""
    if violations:
        extra = ("\n═══ 직전 시도가 아래 이유로 거부됐다. 반드시 고쳐라 ═══\n"
                 + "\n".join(f"- {v}" for v in violations))

    out = generate_json(
        PROMPT.format(
            rules=rules, company=jd.company, job_title=jd.job_title,
            resp=_fmt(jd.responsibilities), req=_fmt(jd.requirements), pref=_fmt(jd.preferred),
            priorities=", ".join(gap.top_priorities) or "-",
            not_exp=", ".join(gap.not_experienced) or "-",
            pool=_pool_text(pj), have=", ".join(have), not_yet=", ".join(not_yet),
            sides="\n".join(sides), allowed_numbers=_fmt(allowed, 60), extra=extra),
        ComposeOut, model=MODEL_WRITE, temperature=0.35)

    if not isinstance(out, ComposeOut):
        out = ComposeOut.model_validate_json(out)
    return build_slots(out, jd, pj)


def build_slots(out: ComposeOut, jd: JD, pj: dict) -> dict:
    """LLM 선택 + 원본 데이터 → 렌더용 슬롯. 수치가 든 문장은 여기서 원문 그대로 들어간다."""
    by_id = {b["id"]: b for b in pj["main_project"]["blocks"]}
    blocks = []
    for ch in out.blocks:
        src = by_id.get(ch.block_id)
        if not src:
            continue
        pool = src["bullets"]
        idxs = [i for i in ch.bullet_indices if 0 <= i < len(pool)][:4] or [0, 1]
        blocks.append({
            "title": ch.title or src["title"],
            "period": src["period"],
            "scope": src.get("scope", ""),
            "bullets": [" ".join(pool[i]["text"].split()) for i in idxs],
            "tech": ", ".join(src["tech"]),
        })

    m = pj["main_project"]
    rb = (f'<b>본인 단독</b> {m["role_boundary"]["solo"]} ／ <b>본인 주도</b> {out.role_boundary_led}'
          f' ／ <b>팀 공동</b> {m["role_boundary"]["team_shared"]}')

    side_map = {s["id"]: s for s in pj["side_projects"]}
    sides = [{"title": s["title"], "meta": s["meta"],
              "text": " ".join(s["text"].split()), "tech": s["tech"]}
             for sid in out.side_project_ids if (s := side_map.get(sid))]

    # 기존 이력서들과 같은 관용 시작구를 결정적으로 보장한다
    note = (out.honesty_note or "").strip()
    if not note.startswith("정직하게"):
        note = "정직하게 밝힙니다 — " + note

    c = pj["career"]
    return {
        "company": jd.company, "job_title": jd.job_title,
        "header": pj["header"], "show_overseas": False,
        "career_first": out.career_first,
        "tagline": out.tagline,
        "core": [{"title": x.title, "body": x.body} for x in out.core[:4]],
        "main": {
            "org": m["org"], "emphasis": out.emphasis, "period": m["period"],
            "participation": m["participation"], "team": m["team"], "env": m["env"],
            "role_boundary": rb,
        },
        "blocks": blocks,
        "career": {**{k: c[k] for k in ("org", "period", "type", "team", "exit")},
                   "bullets": [" ".join(b["text"].split()) for b in c["bullets"]]},
        "side_projects": sides,
        "education": pj["education"], "research": pj["research"], "links": pj["links"],
        "skill_groups": [
            {"label": out.skill_group1_label, "chips": out.skill_group1_chips},
            {"label": out.skill_group2_label, "chips": out.skill_group2_chips},
        ],
        "not_yet_chips": out.not_yet_chips,
        "honesty_note": note,
    }
