"""공고 한 건을 이력서 PDF 까지 밀어 넣는 LangGraph.

되돌림 루프가 두 개 있어서 자유 도구 호출 에이전트가 아니라 명시적 StateGraph 로 짰다.
두 루프 모두 모델이 판단하면 안 되고 코드가 강제해야 하는 구간이다.

  compose ─→ fact_guard ─(위반)─→ compose        (최대 MAX_FACT_RETRIES 회)
  render  ─→ verify_pages ─(>2p)─→ trim ─→ render (최대 MAX_TRIM_ROUNDS 회)
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from langgraph.graph import END, StateGraph

from .config import (MAX_FACT_RETRIES, MAX_PAGES, MAX_TRIM_ROUNDS, PHOTO_SRC,
                     RESUME_HTML_NAME, RESUME_PDF_NAME)
from .guards.fact_guard import FactGuard
from .nodes import compose as compose_mod
from .nodes import fit_gate as fit_mod
from .nodes import gap_analyze as gap_mod
from .nodes.finalize import finalize, record_skipped
from .nodes.parse_jd import parse_jd_with_fallback
from .render.edge_pdf import html_to_pdf
from .render.jinja import render_html
from .render.page_count import count_pages
from .render.trim import trim_once
from .state import JobState

_guard = FactGuard()


# ── 노드 ────────────────────────────────────────────────────────────────
def n_ingest(s: JobState) -> JobState:
    c = s["candidate"]
    jd, ing = parse_jd_with_fallback(c.url)
    if jd is None:
        return {"outcome": "실패", "reason": f"공고 파싱 실패 ({ing.error or '내용 없음'})"}
    if not jd.company:
        jd.company = c.company
    if not jd.job_title:
        jd.job_title = c.title
    print(f"    ingest[{ing.mode}] {jd.company} / {jd.job_title} "
          f"— 담당 {len(jd.responsibilities)} 자격 {len(jd.requirements)} 우대 {len(jd.preferred)}")
    return {"jd": jd, "ingest_mode": ing.mode}


def n_fit(s: JobState) -> JobState:
    fit = fit_mod.fit_gate(s["jd"])
    yrs = fit.min_years_required
    print(f"    fit={fit.score} 요구경력하한={'미명시' if yrs < 0 else str(yrs) + '년'} — {fit.reason[:60]}")
    ok, why = fit_mod.evaluate(fit)
    if not ok:
        return {"fit": fit, "outcome": "제외", "reason": why}
    return {"fit": fit}


def n_gap(s: JobState) -> JobState:
    gap = gap_mod.gap_analyze(s["jd"])
    print(f"    gap: 판정 {len(gap.items)}건 · 미경험 {len(gap.not_experienced)}건")
    return {"gap": gap}


def n_compose(s: JobState) -> JobState:
    r = int(s.get("fact_round", 0))
    slots = compose_mod.compose(s["jd"], s["gap"], s.get("violations"))
    return {"slots": slots, "fact_round": r + 1}


def _jd_text(jd) -> str:
    return " ".join([*jd.responsibilities, *jd.requirements, *jd.preferred,
                     jd.experience_level or "", jd.job_title or ""])


def n_fact_guard(s: JobState) -> JobState:
    # 공고 원문 수치는 인용으로 허용 (본인 주장으로 쓰면 career 검사가 잡는다)
    res = _guard.check(s["slots"], _jd_text(s["jd"]))
    if res.ok:
        print(f"    fact_guard 통과 (시도 {s.get('fact_round')}회)")
        return {"violations": []}
    vs = [str(v) for v in res.violations]
    print(f"    fact_guard 위반 {len(vs)}건 (시도 {s.get('fact_round')}회)")
    for v in vs[:5]:
        print(f"      {v}")
    return {"violations": vs}


_warned_photo = False


def n_render(s: JobState) -> JobState:
    global _warned_photo
    tmp = Path(tempfile.gettempdir()) / "resume_agent_render"
    tmp.mkdir(parents=True, exist_ok=True)
    if not (tmp / "photo.jpg").exists():
        # 사진이 없어도 렌더는 계속한다 (사진 칸만 비고 나머지는 그대로 나온다)
        if PHOTO_SRC.exists():
            shutil.copyfile(PHOTO_SRC, tmp / "photo.jpg")
        elif not _warned_photo:
            print(f"    [warn] 증명사진이 없습니다 ({PHOTO_SRC}) — 사진 없이 렌더합니다")
            _warned_photo = True
    html_p, pdf_p = tmp / RESUME_HTML_NAME, tmp / RESUME_PDF_NAME
    html_p.write_text(render_html(s["slots"]), encoding="utf-8")
    html_to_pdf(html_p, pdf_p)
    return {"html_path": str(html_p), "pdf_path": str(pdf_p)}


def n_verify(s: JobState) -> JobState:
    n = count_pages(s["pdf_path"])
    print(f"    {n}페이지")
    return {"pages": n}


def n_trim(s: JobState) -> JobState:
    r = int(s.get("trim_round", 0))
    slots, what = trim_once(s["slots"], r)
    print(f"    ✂ {what}")
    return {"slots": slots, "trim_round": r + 1, "trims": [*(s.get("trims") or []), what]}


def n_finalize(s: JobState) -> JobState:
    out = finalize(s["slots"], Path(s["html_path"]).read_text(encoding="utf-8"),
                   Path(s["pdf_path"]), s["candidate"], s["jd"],
                   s["fit"], s.get("gap"), s["pages"], s.get("trims") or [],
                   s.get("ingest_mode", "text"))
    print(f"    ✅ {out}")
    return {"outcome": "생성", "out_dir": str(out)}


def n_skip(s: JobState) -> JobState:
    record_skipped(s["candidate"], s.get("jd"),
                   getattr(s.get("fit"), "score", 0), s.get("reason", ""))
    print(f"    ⏭  제외 — {s.get('reason','')}")
    return {}


# ── 분기 ────────────────────────────────────────────────────────────────
def after_ingest(s: JobState) -> str:
    return "skip" if s.get("outcome") in ("실패", "제외") else "fit"


def after_fit(s: JobState) -> str:
    return "skip" if s.get("outcome") == "제외" else "gap"


def after_guard(s: JobState) -> str:
    """위반이 없으면 렌더로. 있으면 재작성, 한도를 넘으면 PDF 를 만들지 않고 포기한다."""
    if not s.get("violations"):
        return "render"
    if int(s.get("fact_round", 0)) > MAX_FACT_RETRIES:
        return "give_up"
    return "compose"


def after_verify(s: JobState) -> str:
    if s.get("pages", 99) <= MAX_PAGES:
        return "finalize"
    if int(s.get("trim_round", 0)) >= MAX_TRIM_ROUNDS:
        return "finalize"          # 더 못 줄이면 있는 그대로 낸다 (zoom 은 건드리지 않는다)
    return "trim"


def n_give_up(s: JobState) -> JobState:
    reason = f"팩트 가드 {MAX_FACT_RETRIES + 1}회 실패: " + "; ".join((s.get("violations") or [])[:3])
    record_skipped(s["candidate"], s.get("jd"), getattr(s.get("fit"), "score", 0), reason)
    print(f"    ❌ {reason}")
    return {"outcome": "실패", "reason": reason}


# ── 조립 ────────────────────────────────────────────────────────────────
def build_graph():
    g = StateGraph(JobState)
    for name, fn in [("ingest", n_ingest), ("fit", n_fit), ("gap", n_gap),
                     ("compose", n_compose), ("fact_guard", n_fact_guard),
                     ("render", n_render), ("verify", n_verify), ("trim", n_trim),
                     ("finalize", n_finalize), ("skip", n_skip), ("give_up", n_give_up)]:
        g.add_node(name, fn)

    g.set_entry_point("ingest")
    g.add_conditional_edges("ingest", after_ingest, {"fit": "fit", "skip": "skip"})
    g.add_conditional_edges("fit", after_fit, {"gap": "gap", "skip": "skip"})
    g.add_edge("gap", "compose")
    g.add_edge("compose", "fact_guard")
    g.add_conditional_edges("fact_guard", after_guard,
                            {"render": "render", "compose": "compose", "give_up": "give_up"})
    g.add_edge("render", "verify")
    g.add_conditional_edges("verify", after_verify, {"finalize": "finalize", "trim": "trim"})
    g.add_edge("trim", "render")
    for t in ("finalize", "skip", "give_up"):
        g.add_edge(t, END)
    return g.compile()


GRAPH = None


def run_one(candidate) -> JobState:
    global GRAPH
    if GRAPH is None:
        GRAPH = build_graph()
    return GRAPH.invoke({"candidate": candidate, "fact_round": 0, "trim_round": 0,
                         "violations": [], "trims": []},
                        {"recursion_limit": 50})
