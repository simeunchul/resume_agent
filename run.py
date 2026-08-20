"""이력서 에이전트 배치 실행 — 수집 → 공고별 그래프 → 요약.

    python run.py                 # 기본 실행
    python run.py --limit 3       # 이력서 3건까지만
    python run.py --dry           # 수집·필터까지만 보고 멈춤
    python run.py --url <URL>     # 공고 URL 한 건만 처리
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from datetime import datetime

try:
    from resume_agent.config import DAILY_RESUME_CAP, RUNS_DIR, SEARCH_KEYWORDS
    from resume_agent.graph import run_one
    from resume_agent.queue_view import build_queue
    from resume_agent.sources.base import JobCandidate
    from resume_agent.sources.collect import collect_all
except ModuleNotFoundError as e:      # 전역 파이썬으로 실행하면 여기로 온다
    raise SystemExit(
        "\n".join([
            "",
            f"[!] '{e.name}' 을(를) 찾지 못했습니다 — 이 프로젝트의 venv 로 실행해야 합니다.",
            "",
            "    run.bat --limit 3",
            r"    또는  .venv\Scripts\python.exe run.py --limit 3",
            "",
            "  venv 가 아직 없다면:",
            "    python -m venv .venv",
            r"    .venv\Scripts\python.exe -m pip install -e .",
            r"    .venv\Scripts\python.exe -m playwright install chromium",
            "",
        ])
    ) from e

# 윈도우 콘솔이 cp949 라서 한글 출력이 깨진다
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=DAILY_RESUME_CAP)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--url", type=str, default="")
    ap.add_argument("--jobkorea", action="store_true", help="잡코리아도 수집 (이미지 공고라 느리다)")
    ap.add_argument("--queue", action="store_true", help="수집·생성 없이 지원 대기열만 다시 만든다")
    args = ap.parse_args()

    if args.queue:
        print(f"지원대기열: {build_queue()}")
        return

    t0 = time.time()
    day = datetime.now().strftime("%Y-%m-%d")
    run_dir = RUNS_DIR / day
    run_dir.mkdir(parents=True, exist_ok=True)

    if args.url:
        cands = [JobCandidate(source="manual", source_id=args.url.rsplit("/", 1)[-1],
                              url=args.url, title="", company="")]
        stats = {"per_source": {"manual": 1}, "raw": 1, "unique": 1, "fresh": 1}
    else:
        print(f"수집 시작 — 키워드 {len(SEARCH_KEYWORDS)}개")
        r = collect_all(use_jobkorea=args.jobkorea)
        cands = r.pop("relevant")
        stats = r
        print(f"  소스별 {stats['per_source']}")
        print(f"  원시 {stats['raw']} → 중복제거 {stats['unique']} → 신규 {stats['fresh']} → 관련 {len(cands)}")

    if args.dry:
        for c in cands[:40]:
            print(f"  [{c.source:7s}] {c.title[:56]:56s} | {c.company[:16]}")
        print(f"\n(dry) 총 {len(cands)}건")
        return

    made, skipped, failed, rows = 0, 0, 0, []
    for i, c in enumerate(cands, 1):
        if made >= args.limit:
            print(f"\n하루 생성 상한 {args.limit}건 도달 — 나머지 {len(cands)-i+1}건은 다음 실행으로")
            break
        print(f"\n[{i}/{len(cands)}] {c.company or '?'} / {c.title or c.url}")
        try:
            st = run_one(c)
        except Exception as e:  # noqa: BLE001 - 한 건이 죽어도 배치는 계속
            print(f"    ❌ 예외: {type(e).__name__}: {e}")
            failed += 1
            rows.append((c, "실패", f"{type(e).__name__}: {e}", None))
            continue
        oc = st.get("outcome", "실패")
        rows.append((c, oc, st.get("reason", ""), st))
        if oc == "생성":
            made += 1
        elif oc == "제외":
            skipped += 1
        else:
            failed += 1

    # 요약
    lines = [f"# 실행 요약 {day}", "",
             f"- 소요 {time.time()-t0:.0f}초",
             f"- 수집 {stats.get('raw',0)}건 → 중복제거 {stats.get('unique',0)} → 관련 {len(cands)}",
             f"- **이력서 생성 {made}건** / 게이트 제외 {skipped} / 실패 {failed}", "",
             "| 결과 | 회사 | 직무 | 적합도 | 페이지 | 공고 URL |", "|---|---|---|---|---|---|"]
    for c, oc, reason, st in rows:
        jd = (st or {}).get("jd")
        fit = getattr((st or {}).get("fit"), "score", "")
        mark = {"생성": "✅", "제외": "⏭", "실패": "❌"}.get(oc, "?")
        lines.append(f"| {mark} {oc} | {getattr(jd,'company',c.company)} | "
                     f"{getattr(jd,'job_title',c.title)} | {fit} | {(st or {}).get('pages','')} | {c.url} |")
    fails = [(c, r) for c, oc, r, _ in rows if oc != "생성"]
    if fails:
        lines += ["", "## 생성되지 않은 사유"]
        lines += [f"- {c.company or c.url} — {r}" for c, r in fails]

    (run_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{'='*70}")
    print(f"생성 {made} / 제외 {skipped} / 실패 {failed} · {time.time()-t0:.0f}초")
    print(f"요약: {run_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
