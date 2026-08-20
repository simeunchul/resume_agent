"""입사지원 자동화 가능성 조사 — 실제 구조를 확인한다."""
import io, json, ssl, sys, urllib.parse, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CTX=ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE
def get(u,h=None,t=20):
    r=urllib.request.Request(u,headers={"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9",**(h or {})})
    try:
        with urllib.request.urlopen(r,timeout=t,context=CTX) as x: return x.status,x.read()
    except urllib.error.HTTPError as e: return e.code,e.read()[:400]
    except Exception as e: return None,f"{type(e).__name__}: {e}".encode()

print("### 1. 원티드 — 외부지원(is_outlink) 비율")
tot=out=0; samples=[]
for kw in ["AI 엔지니어","LLM","데이터 엔지니어","MLOps"]:
    st,b=get("https://www.wanted.co.kr/api/chaos/search/v1/results?query="+urllib.parse.quote(kw)+"&tab=position")
    if st!=200: continue
    for p in (json.loads(b).get("positions") or {}).get("data") or []:
        tot+=1
        if p.get("is_outlink"):
            out+=1; samples.append((p.get("position"), (p.get("company") or {}).get("name")))
print(f"  표본 {tot}건 중 외부지원 {out}건 ({out/max(tot,1)*100:.0f}%)")
for s in samples[:5]: print(f"    - {s[0]} / {s[1]}")
print("  → 외부지원은 회사 자체 채용페이지로 나가므로 폼이 제각각이다")

print("\n### 2. 원티드 robots.txt — 지원 관련 경로")
st,b=get("https://www.wanted.co.kr/robots.txt")
txt=b.decode("utf-8","replace") if st==200 else ""
print("\n".join("  "+l for l in txt.splitlines()[:40]))

print("\n### 3. 점핏 robots.txt")
st,b=get("https://jumpit.saramin.co.kr/robots.txt")
print("\n".join("  "+l for l in (b.decode("utf-8","replace") if st==200 else str(b)).splitlines()[:25]))
