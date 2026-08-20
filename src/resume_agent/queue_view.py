"""지원 대기열 — 만들어 둔 이력서 중 아직 지원하지 않은 것을 한 장에 모은다.

자동 지원은 하지 않는다 (원티드 약관이 자동화된 로그인·게재를 금지, 점핏 robots 가
지원 경로를 Disallow). 대신 '공고 열기 → 이력서 첨부' 를 최소 클릭으로 끝내게 돕는다.

지원했으면 그 폴더의 `공고.md` 에서 `- [ ] 지원함` 을 `- [x]` 로 바꾸면 대기열에서 빠진다.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import LEDGER, RESUME_PDF_NAME, RESUME_ROOT

QUEUE_FILE = RESUME_ROOT / "_지원대기열.md"


def _applied(folder: Path) -> bool:
    note = folder / "공고.md"
    if not note.exists():
        return False
    return "- [x] 지원함" in note.read_text(encoding="utf-8").replace("- [X]", "- [x]")


def _due_key(row: dict) -> str:
    d = (row.get("deadline") or "").strip()
    return d if d and d[0].isdigit() else "9999"      # 상시채용은 뒤로


def build_queue() -> Path:
    if not Path(LEDGER).exists():
        return QUEUE_FILE
    rows = [json.loads(l) for l in Path(LEDGER).read_text(encoding="utf-8").splitlines() if l.strip()]

    latest: dict[str, dict] = {}
    for r in rows:
        if r.get("status") == "생성":
            latest[r["folder"]] = r          # 같은 폴더는 마지막 것만

    pending, done = [], []
    for folder, r in latest.items():
        p = Path(folder)
        if not p.exists():
            continue
        (done if _applied(p) else pending).append((p, r))
    pending.sort(key=lambda x: _due_key(x[1]))

    L = [f"# 지원 대기열  ·  {datetime.now():%Y-%m-%d %H:%M}", "",
         f"**미지원 {len(pending)}건** / 지원 완료 {len(done)}건", "",
         "지원했으면 그 폴더의 `공고.md` 에서 `- [ ] 지원함` 을 `- [x]` 로 바꾸세요. 다음 실행 때 목록에서 빠집니다.",
         "", "---", ""]

    if pending:
        L += ["## 미지원", "", "| 마감 | 적합도 | 회사 · 직무 | 공고 | 이력서 |", "|---|---|---|---|---|"]
        for p, r in pending:
            due = r.get("deadline") or "상시"
            due = due[:10] if due[:1].isdigit() else due
            pdf = (p / RESUME_PDF_NAME).resolve().as_uri()
            L.append(f"| {due} | {r.get('fit_score','')} | **{r['company']}** · {r['job_title']} "
                     f"| [공고 열기]({r['url']}) | [PDF]({pdf}) |")
        L += ["", "### 폴더 경로 (파일 첨부용)", ""]
        for p, r in pending:
            L.append(f"- **{r['company']}** — `{p}`")
        L += [""]
    else:
        L += ["## 미지원", "", "없음 — 전부 지원했습니다.", ""]

    if done:
        L += ["---", "", "## 지원 완료", ""]
        for p, r in done:
            L.append(f"- ~~{r['company']} · {r['job_title']}~~ — {r['url']}")
        L += [""]

    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text("\n".join(L), encoding="utf-8")
    return QUEUE_FILE
