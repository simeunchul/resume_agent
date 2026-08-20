import io,sys,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
with sync_playwright() as pw:
    br=pw.chromium.launch(headless=True)
    ctx=br.new_context(user_agent=UA,locale="ko-KR",viewport={"width":1440,"height":1200})
    pg=ctx.new_page()
    pg.goto("https://www.jobkorea.co.kr/Recruit/GI_Read/49074852",wait_until="networkidle",timeout=60000)
    pg.wait_for_timeout(4000)

    print("### 프레임 전체")
    for f in pg.frames:
        try: t=f.inner_text("body"); print(f"  url={f.url[:95]}\n      len={len(t)}  head={t[:90]!r}")
        except Exception as e: print(f"  url={f.url[:95]} ERR={type(e).__name__}")

    print("\n### 상세요강 영역 DOM 구조")
    for sel in ["#tbCont","#devDetail",".detailArea",".view-detail","#content .detail",
                "[class*=detail]","[id*=Detail]","[id*=detail]","iframe"]:
        try:
            n=pg.eval_on_selector_all(sel,"els=>els.length")
            if n: print(f"  {sel:24s} -> {n}개")
        except Exception: pass

    print("\n### iframe 상세")
    ifr=pg.eval_on_selector_all("iframe","els=>els.map(e=>({id:e.id,src:e.getAttribute('src'),w:e.clientWidth,h:e.clientHeight}))")
    for i in ifr: print("  ",i)

    print("\n### 큰 이미지 목록 (상세요강이 이미지인지 확인)")
    imgs=pg.eval_on_selector_all("img","els=>els.filter(e=>e.naturalWidth>300).map(e=>({src:e.src.slice(0,110),w:e.naturalWidth,h:e.naturalHeight}))")
    for i in imgs: print("  ",i)

    print("\n### '상세요강' 텍스트 노드 주변")
    try:
        loc=pg.get_by_text("상세요강").first
        print("  found:", loc.evaluate("e=>e.outerHTML.slice(0,300)"))
    except Exception as e: print("  ",e)
    br.close()
