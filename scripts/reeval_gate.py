"""기존 생성분을 바뀐 게이트 기준으로 재평가한다.

공고.md 에 JD 원문이 남아 있으므로 재수집 없이 파싱해서 fit_gate 만 다시 돌린다.
탈락한 폴더는 지우지 않고 runs/_제외됨_{날짜}/ 로 옮긴다 — 되돌릴 수 있게.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from resume_agent.config import LEDGER, RUNS_DIR
from resume_agent.nodes.fit_gate import fit_gate, passes
from resume_agent.queue_view import build_queue
from resume_agent.schemas import JD

_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|$", re.M)


def parse_note(text: str) -> JD:
    """공고.md 를 JD 로 되돌린다."""
    fields = {k.strip(): v.strip() for k, v in _ROW.findall(text) if k.strip() and k.strip() != "---"}
    title = re.search(r"^#\s*(.+?)\s*—\s*(.+)$", text, re.M)
    company, job = (title.group(1), title.group(2)) if title else ("", "")

    def section(name: str) -> list[str]:
        m = re.search(rf"^##\s*{name}[^\n]*\n(.*?)(?=^##|\Z)", text, re.M | re.S)
        if not m:
            return []
        out = []
        for line in m.group(1).splitlines():
            line = line.strip()
            if line.startswith("- ") and "공고에 명시 없음" not in line:
                out.append(line[2:].strip())
        return out

    stack = fields.get("기술스택", "")
    return JD(
        company=company, job_title=job,
        responsibilities=section("담당업무"),
        requirements=section(r"자격요건"),
        preferred=section("우대사항"),
        tech_stack=[x.strip() for x in stack.split(",") if x.strip()],
        employment_type=fields.get("고용형태", "").strip("-").strip(),
        deadline=fields.get("마감", ""),
        location=fields.get("근무지", "").strip("-").strip(),
        experience_level=fields.get("경력요건", "").strip("-").strip(),
    )


def main() -> None:
    rows = [json.loads(l) for l in Path(LEDGER).read_text(encoding="utf-8").splitlines() if l.strip()]
    made: dict[str, dict] = {}
    for r in rows:
        if r.get("status") == "생성":
            made[r["folder"]] = r

    archive = RUNS_DIR / f"_제외됨_{datetime.now():%Y%m%d}"
    kept, dropped = [], []

    for folder, rec in made.items():
        d = Path(folder)
        note = d / "공고.md"
        if not d.exists() or not note.exists():
            print(f"  건너뜀 (공고.md 없음) {d.name}")
            continue
        jd = parse_note(note.read_text(encoding="utf-8"))
        fit = fit_gate(jd)
        ok = passes(fit)
        mark = "✅ 유지" if ok else "❌ 탈락"
        print(f"  {mark}  {d.name[:40]:40s} {rec['fit_score']} → {fit.score}  "
              f"[{jd.experience_level or '연차 명시 없음'}]")
        if not ok:
            for b in fit.blockers:
                print(f"          └ {b[:100]}")
            archive.mkdir(parents=True, exist_ok=True)
            shutil.move(str(d), str(archive / d.name))
            dropped.append((rec, fit))
        else:
            kept.append((rec, fit))

    # 대장 갱신 — 탈락분은 '제외' 로 한 줄 더 남긴다 (중복 재생성 방지)
    if dropped:
        with open(LEDGER, "a", encoding="utf-8") as f:
            for rec, fit in dropped:
                f.write(json.dumps({
                    **{k: rec[k] for k in ("key", "source", "url", "company", "job_title")},
                    "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "fit_score": fit.score, "status": "제외",
                    "reason": "게이트 재평가: " + ("; ".join(fit.blockers) or f"적합도 {fit.score}"),
                }, ensure_ascii=False) + "\n")

    print(f"\n유지 {len(kept)}건 / 탈락 {len(dropped)}건")
    if dropped:
        print(f"탈락분은 지우지 않고 옮겨 뒀습니다 → {archive}")
        print("  되살리려면 폴더를 원래 위치로 옮기거나  run.bat --url <주소>  로 다시 만드세요.")
    print(f"대기열 갱신: {build_queue()}")


if __name__ == "__main__":
    main()
