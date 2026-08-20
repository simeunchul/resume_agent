import io, ssl, sys, urllib.request, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CTX=ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE
def get(u,t=20):
    r=urllib.request.Request(u,headers={"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9"})
    try:
        with urllib.request.urlopen(r,timeout=t,context=CTX) as x: return x.status,x.read()
    except Exception as e: return None,f"{type(e).__name__}: {e}".encode()

print("### 원티드 robots.txt (원문)")
st,b=get("https://www.wanted.co.kr/robots.txt")
print(f"status={st} bytes={len(b)}")
print(b.decode("utf-8","replace")[:1500])
print("="*90)

print("### 원티드 이용약관에서 자동화 관련 조항 찾기")
for u in ["https://www.wanted.co.kr/terms","https://www.wanted.co.kr/help/terms",
          "https://static.wanted.co.kr/terms/terms.html"]:
    st,b=get(u)
    print(f"  {u} -> {st} ({len(b)}B)")
    if st==200:
        t=re.sub(r"<[^>]+>"," ",b.decode("utf-8","replace"))
        t=re.sub(r"\s+"," ",t)
        for kw in ["자동","크롤","봇 ","로봇","스크래","매크로","프로그램을 이용","비정상적인 방법","자동화"]:
            for m in re.finditer(kw,t):
                seg=t[max(0,m.start()-90):m.start()+150].strip()
                if len(seg)>60:
                    print(f"    [{kw}] …{seg}…"); break
