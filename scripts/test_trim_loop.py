"""분량 루프 검증 — 일부러 3페이지를 만든 뒤 zoom 유지한 채 2페이지로 돌아오는지."""
import io, json, shutil, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from resume_agent.render.jinja import write_html
from resume_agent.render.edge_pdf import html_to_pdf
from resume_agent.render.page_count import count_pages
from resume_agent.render.trim import trim_once
from resume_agent.config import (PHOTO_SRC, MAX_PAGES, MAX_TRIM_ROUNDS,
                                 RESUME_HTML_NAME, RESUME_PDF_NAME)

out = Path("runs/_trim_test"); out.mkdir(parents=True, exist_ok=True)
shutil.copyfile(PHOTO_SRC, out / "photo.jpg")
slots = json.load(open("scripts/reference_slots.json", encoding="utf-8"))

# 일부러 부풀린다 — 각 블록에 bullet 을 추가
import yaml
P = yaml.safe_load(io.open("profile/projects.yaml", encoding="utf-8"))
for i, src in enumerate(P["main_project"]["blocks"][:len(slots["blocks"])]):
    extra = [" ".join(b["text"].split()) for b in src["bullets"]]
    slots["blocks"][i]["bullets"] = extra          # 풀 전체를 넣어 과적재
print(f"부풀린 bullet 수: {[len(b['bullets']) for b in slots['blocks']]}")

html_p, pdf_p = out / RESUME_HTML_NAME, out / RESUME_PDF_NAME
for rnd in range(MAX_TRIM_ROUNDS + 1):
    write_html(slots, html_p); html_to_pdf(html_p, pdf_p)
    n = count_pages(pdf_p)
    h = html_p.read_text(encoding="utf-8")
    zoom_ok = "zoom:1" in h and "font-size:10pt" in h
    print(f"[round {rnd}] {n}페이지 | zoom:1·10pt 유지={zoom_ok} | bullets={[len(b['bullets']) for b in slots['blocks']]} | 기타={len(slots['side_projects'])}")
    if n <= MAX_PAGES:
        print(f"  ✅ {MAX_PAGES}페이지로 복귀 (zoom 미변경)")
        break
    slots, what = trim_once(slots, rnd)
    print(f"  ✂  {what}")
else:
    print(f"  ❌ {MAX_TRIM_ROUNDS}회로 부족")
