import io, json, shutil, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from resume_agent.render.jinja import write_html
from resume_agent.render.edge_pdf import html_to_pdf
from resume_agent.render.page_count import count_pages
from resume_agent.render.trim import trim_once
from resume_agent.config import (PHOTO_SRC, MAX_PAGES, MAX_TRIM_ROUNDS,
                                 RESUME_HTML_NAME, RESUME_PDF_NAME, RESUME_ROOT)

out = Path("runs/_render_test"); out.mkdir(parents=True, exist_ok=True)
shutil.copyfile(PHOTO_SRC, out / "photo.jpg")

slots = json.load(open("scripts/reference_slots.json", encoding="utf-8"))

html_p, pdf_p = out / RESUME_HTML_NAME, out / RESUME_PDF_NAME
for rnd in range(MAX_TRIM_ROUNDS + 1):
    write_html(slots, html_p)
    html_to_pdf(html_p, pdf_p)
    n = count_pages(pdf_p)
    print(f"[round {rnd}] HTML {html_p.stat().st_size:,}B → PDF {pdf_p.stat().st_size:,}B · {n}페이지")
    if n <= MAX_PAGES:
        print(f"  ✅ {MAX_PAGES}페이지 이내 — 완료")
        break
    slots, what = trim_once(slots, rnd)
    print(f"  ✂  {what}")
else:
    print(f"  ❌ {MAX_TRIM_ROUNDS}회 덜어내고도 초과")

# 기존에 만들어 둔 PDF 가 있으면 비교한다 (렌더러가 바뀌면 페이지 경계가 흔들린다)
ref = next(RESUME_ROOT.glob(f"*/{RESUME_PDF_NAME}"), None) if RESUME_ROOT.exists() else None
if ref and ref.exists():
    print(f"\n기존 PDF({ref.parent.name}): {count_pages(ref)}페이지 ({ref.stat().st_size:,}B)")
    print(f"생성된 PDF     : {count_pages(pdf_p)}페이지 ({pdf_p.stat().st_size:,}B)")

# zoom 이 건드려지지 않았는지 확인
h = html_p.read_text(encoding="utf-8")
print(f"\nzoom:1 유지: {'zoom:1' in h}")
print(f"font-size:10pt 유지: {'font-size:10pt' in h}")
print(f"점선칩 그룹 존재: {'chip off' in h}")
print(f"정직 표기 note 존재: {'정직하게 밝힙니다' in h}")
