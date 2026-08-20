import io, re, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
with sync_playwright() as pw:
    br=pw.chromium.launch(headless=True)
    ctx=br.new_context(user_agent=UA,locale="ko-KR",viewport={"width":1440,"height":1000})
    pg=ctx.new_page()

    print("### A. joblist 페이지의 실제 링크 구조")
    pg.goto("https://www.jobkorea.co.kr/recruit/joblist?menucode=duty",wait_until="domcontentloaded",timeout=45000)
    pg.wait_for_timeout(4000)
    hrefs=pg.eval_on_selector_all("a[href]","els=>els.map(e=>e.getAttribute('href')).filter(Boolean)")
    print(f"  a 태그 {len(hrefs)}개")
    from collections import Counter
    pat=Counter()
    for h in hrefs:
        m=re.match(r'(/[^/?]+/?[^/?]*)',h)
        if m: pat[m.group(1)]+=1
    for p,c in pat.most_common(15): print(f"    {p}  x{c}")
    # 카테고리 관련 파라미터 찾기
    params=Counter()
    for h in hrefs:
        for k in re.findall(r'[?&]([A-Za-z_]+)=',h): params[k]+=1
    print(f"  쿼리 파라미터 빈도: {dict(params.most_common(12))}")
    open("scripts/_joblist_links.txt","w",encoding="utf-8").write("\n".join(sorted(set(hrefs))))

    print("\n### B. GI_Read 본문 텍스트 실물 (안랩 공고)")
    pg.goto("https://www.jobkorea.co.kr/Recruit/GI_Read/49074852",wait_until="domcontentloaded",timeout=45000)
    pg.wait_for_timeout(3500)
    body=pg.inner_text("body")
    open("scripts/_gi_read_body.txt","w",encoding="utf-8").write(body)
    print(f"  총 {len(body)}자. 앞 1800자:")
    print("  " + body[:1800].replace("\n","\n  "))
    print("\n  --- frames ---")
    for f in pg.frames:
        try:
            t=f.inner_text("body")
            print(f"    frame url={f.url[:80]} len={len(t)}")
        except Exception as e:
            print(f"    frame url={f.url[:80]} ERR={type(e).__name__}")
    br.close()
