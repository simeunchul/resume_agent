import io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
TARGETS=[("wanted","https://www.wanted.co.kr/wd/381470","AI Agent 엔지니어 / 크라우드웍스"),
         ("wanted","https://www.wanted.co.kr/wd/381506","AI 플랫폼 운영 엔지니어 / 아일리스프런티어"),
         ("wanted","https://www.wanted.co.kr/wd/381041","LLM 엔지니어 / 버블탭"),
         ("jumpit","https://jumpit.saramin.co.kr/position/54787941","백엔드 / 텐빌리언")]
KWS=["담당업무","주요업무","자격요건","자격 요건","필수","우대사항","우대 사항","자격","기술스택","이런 분"]
with sync_playwright() as pw:
    br=pw.chromium.launch(headless=True)
    ctx=br.new_context(user_agent=UA,locale="ko-KR",viewport={"width":1440,"height":1200})
    pg=ctx.new_page()
    for src,url,label in TARGETS:
        try:
            pg.goto(url,wait_until="domcontentloaded",timeout=60000); pg.wait_for_timeout(4000)
            # 원티드는 '상세 정보 더 보기' 버튼이 있음
            for name in ["상세 정보 더 보기","더 보기","펼쳐보기"]:
                try:
                    b=pg.get_by_role("button",name=name)
                    if b.count(): b.first.click(timeout=3000); pg.wait_for_timeout(1500)
                except Exception: pass
            t=pg.inner_text("body")
            imgs=pg.eval_on_selector_all("img","els=>els.filter(e=>e.naturalWidth>300).map(e=>e.naturalHeight)")
            print(f"[{src}] {label}")
            print(f"   {url}")
            print(f"   텍스트 {len(t):,}자 | 큰이미지 {len(imgs)}개(총 {sum(imgs):,}px)")
            found=[k for k in KWS if k in t]
            print(f"   섹션 키워드: {found}")
            i=max([t.find(k) for k in ["주요업무","담당업무","자격요건"] if k in t] or [-1])
            if i>=0: print(f"   본문 발췌: {t[i:i+320].replace(chr(10),' | ')}")
            print("   "+"-"*82)
        except Exception as e:
            print(f"[{src}] {label} 실패: {type(e).__name__}: {e}")
    br.close()
