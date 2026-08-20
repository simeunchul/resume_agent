"""기존 폴더에 공고.md 를 채워 넣는다 (URL + 공고 원문 재수집)."""
import io, json, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from types import SimpleNamespace
from resume_agent.config import LEDGER, RESUME_PDF_NAME
from resume_agent.nodes.jd_note import write_jd_note
from resume_agent.nodes.parse_jd import parse_jd_with_fallback
from resume_agent.render.page_count import count_pages

rows = [json.loads(l) for l in Path(LEDGER).read_text(encoding="utf-8").splitlines() if l.strip()]
done = set()
for r in rows:
    if r["status"] != "생성" or r["folder"] in done:
        continue
    done.add(r["folder"])
    d = Path(r["folder"])
    if not d.exists() or (d / "공고.md").exists():
        print(f"  건너뜀 {d.name}"); continue
    print(f"  ▶ {d.name} — 공고 재수집 중…", flush=True)
    try:
        jd, ing = parse_jd_with_fallback(r["url"])
    except Exception as e:
        jd, ing = None, SimpleNamespace(mode="text")
        print(f"     재수집 실패: {type(e).__name__}")
    if jd is None:
        # 최소한 URL 과 대장 정보만이라도 남긴다
        jd = SimpleNamespace(company=r["company"], job_title=r["job_title"],
                             responsibilities=[], requirements=[], preferred=[],
                             tech_stack=[], employment_type="", deadline=r.get("deadline",""),
                             location="", experience_level="")
    cand = SimpleNamespace(url=r["url"], source=r["source"], due=r.get("deadline",""))
    fit = SimpleNamespace(score=r.get("fit_score", 0),
                          reason="(백필 — 최초 생성 시 판정)", blockers=[])
    pages = count_pages(d / RESUME_PDF_NAME)
    p = write_jd_note(d, cand, jd, fit, None, getattr(ing, "mode", "text"), pages, r.get("trims") or [])
    print(f"     ✅ {p.name} (담당 {len(jd.responsibilities)} 자격 {len(jd.requirements)})")
print("백필 완료")
