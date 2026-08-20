"""잡코리아: dutyCtgr 코드 수집 + GI_Read 본문 추출 검증 (Playwright)."""
import io, json, re, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

with sync_playwright() as pw:
    br = pw.chromium.launch(headless=True)
    ctx = br.new_context(user_agent=UA, locale="ko-KR", viewport={"width": 1440, "height": 1000})
    pg = ctx.new_page()

    print("### 1. dutyCtgr 코드 수집")
    pg.goto("https://www.jobkorea.co.kr/recruit/joblist?menucode=duty", wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(3500)
    html = pg.content()
    print(f"  렌더 후 HTML: {len(html):,} bytes")
    pairs = re.findall(r'dutyCtgr=(\d+)[^>]*>\s*([^<]{1,40})', html)
    seen, hits = {}, []
    for code, name in pairs:
        name = re.sub(r'\s+', ' ', name).strip()
        if not name or code in seen:
            continue
        seen[code] = name
    KEY = ["AI", "인공지능", "데이터", "머신", "딥러닝", "빅데이터", "분석", "DBA", "개발", "엔지니어", "서버", "웹"]
    for code, name in seen.items():
        if any(k in name for k in KEY):
            hits.append((code, name))
    print(f"  전체 코드 {len(seen)}개 / 관련 코드 {len(hits)}개")
    for c, n in hits[:40]:
        print(f"    dutyCtgr={c}  {n}")
    json.dump(seen, open("scripts/jobkorea_duty_codes.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("\n### 2. GI_Read 본문 추출 검증")
    for jid in ["49074852", "49480421", "49517249"]:
        url = f"https://www.jobkorea.co.kr/Recruit/GI_Read/{jid}"
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=45000)
            pg.wait_for_timeout(3000)
        except Exception as e:
            print(f"  [{jid}] goto 실패: {e}")
            continue
        body = pg.inner_text("body")
        frames = pg.frames
        print(f"  [{jid}] {pg.title()[:60]}")
        print(f"      body text: {len(body):,}자 | frames: {len(frames)}")
        for kw in ["자격요건", "우대사항", "담당업무", "주요업무", "모집부문", "지원자격", "근무조건"]:
            if kw in body:
                print(f"      ✓ '{kw}' 발견")
        # iframe 안에 본문이 있는 경우
        for f in frames[1:]:
            try:
                ft = f.inner_text("body")
                if len(ft) > 200:
                    print(f"      [iframe {f.url[:70]}] {len(ft):,}자")
                    for kw in ["자격요건", "우대사항", "담당업무"]:
                        if kw in ft:
                            print(f"          ✓ iframe 내 '{kw}'")
            except Exception:
                pass
        imgs = pg.eval_on_selector_all("img", "els => els.filter(e => e.naturalWidth > 400).length")
        print(f"      큰 이미지(>400px) {imgs}개  ← 이미지 공고 판별용")
        print("      " + "-" * 80)
    br.close()
