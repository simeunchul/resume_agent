import io,sys,re,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
IFRM="https://www.jobkorea.co.kr/Recruit/GI_Read_Comt_Ifrm?Gno={g}&isHiringCenter=false&hideMapView=false"

with sync_playwright() as pw:
    br=pw.chromium.launch(headless=True)
    ctx=br.new_context(user_agent=UA,locale="ko-KR",viewport={"width":1440,"height":1200})
    pg=ctx.new_page()

    print("### 1. 상세요강 iframe 직접 열기")
    for g in ["49074852","49517249"]:
        pg.goto(IFRM.format(g=g),wait_until="networkidle",timeout=60000)
        pg.wait_for_timeout(2500)
        t=pg.inner_text("body")
        imgs=pg.eval_on_selector_all("img","els=>els.filter(e=>e.naturalWidth>300).map(e=>({w:e.naturalWidth,h:e.naturalHeight}))")
        tot_h=sum(i["h"] for i in imgs)
        print(f"  [{g}] 텍스트 {len(t):,}자 | 큰이미지 {len(imgs)}개 (총높이 {tot_h:,}px)")
        for kw in ["담당업무","자격요건","우대사항","주요업무","모집분야","지원자격","자격 요건","우대 사항"]:
            if kw in t: print(f"       ✓ '{kw}'")
        print(f"       본문 앞 400자: {t[:400]!r}")
        print("       "+"-"*80)

    print("\n### 2. dutyCtgr=10031 이 무슨 카테고리인지 (제목으로 판단)")
    pg.goto("https://www.jobkorea.co.kr/recruit/joblist?menucode=duty&dutyCtgr=10031",wait_until="domcontentloaded",timeout=60000)
    pg.wait_for_timeout(4000)
    titles=pg.eval_on_selector_all("a[href*='GI_Read']","els=>els.map(e=>e.innerText.trim()).filter(t=>t.length>3).slice(0,15)")
    for t in titles[:12]: print("   -",t.replace("\n"," / ")[:90])

    print("\n### 3. 직무 카테고리 코드 패널 렌더링 시도")
    pg.goto("https://www.jobkorea.co.kr/recruit/joblist?menucode=duty",wait_until="networkidle",timeout=60000)
    pg.wait_for_timeout(5000)
    codes=pg.eval_on_selector_all(
        "a[href*='dutyCtgr'], [data-code], input[type=checkbox][id]",
        "els=>els.slice(0,400).map(e=>({tag:e.tagName,href:e.getAttribute('href'),dc:e.getAttribute('data-code'),id:e.id,txt:(e.innerText||e.value||'').trim().slice(0,30)}))")
    hit=[c for c in codes if c.get("href") or c.get("dc")]
    print(f"  후보 {len(codes)}개 / dutyCtgr·data-code 보유 {len(hit)}개")
    for c in hit[:25]: print("   ",c)
    br.close()
