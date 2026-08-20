import json, ssl, urllib.error, urllib.parse, urllib.request, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CTX = ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE

def get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language":"ko-KR,ko;q=0.9", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:600], dict(e.headers)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".encode(), {}

print("### 1. 잡코리아 robots.txt — User-agent:* 구간 전체")
st, b, _ = get("https://www.jobkorea.co.kr/robots.txt")
print(b.decode("utf-8","replace"))
print("="*100)

print("### 2. 잡코리아 공고 목록 실제 접근")
for label, u in [
    ("joblist AI검색", "https://www.jobkorea.co.kr/recruit/joblist?menucode=duty&dutyCtgr=10031"),
    ("Search 키워드", "https://www.jobkorea.co.kr/Search/?stext=" + urllib.parse.quote("AI 엔지니어")),
]:
    st, b, h = get(u)
    txt = b.decode("utf-8","replace") if st==200 else str(b[:300])
    print(f"[{label}] status={st} bytes={len(b)} ctype={h.get('Content-Type')}")
    if st==200:
        import re
        links = sorted(set(re.findall(r'/Recruit/GI_Read/(\d+)', txt)))
        print(f"    공고ID 추출: {len(links)}건  샘플={links[:8]}")
        print(f"    캡차/차단 흔적: {'captcha' in txt.lower() or '비정상' in txt or '차단' in txt}")
    print("-"*100)

print("### 3. 사람인 오픈API 무키 응답 원문")
st, b, _ = get("https://oapi.saramin.co.kr/job-search?access-key=TEST&keywords=AI&count=5")
print(f"status={st} body={b.decode('utf-8','replace')}")
print("="*100)

print("### 4. 프로그래머스 도메인 재확인")
for u in ["https://career.programmers.co.kr/job", "https://programmers.co.kr/job",
          "https://school.programmers.co.kr/robots.txt", "https://programmers.co.kr/robots.txt"]:
    st, b, _ = get(u, timeout=10)
    print(f"  {u} -> status={st} bytes={len(b)}")
print("="*100)

print("### 5. 원티드 v4 응답 필드 구조")
st, b, _ = get("https://www.wanted.co.kr/api/v4/jobs?country=kr&job_sort=job.latest_order&locations=all&years=-1&limit=3&offset=0")
d = json.loads(b)
print("top keys:", list(d.keys()))
j = d["data"][0]
print("job keys:", list(j.keys()))
print(json.dumps(j, ensure_ascii=False, indent=1)[:1200])
print("="*100)

print("### 6. 점핏 응답 필드 구조")
st, b, _ = get("https://api.jumpit.co.kr/api/positions?sort=reg_dt&highlight=false&page=1")
d = json.loads(b)
print("top keys:", list(d.keys()), "| result keys:", list(d.get("result",{}).keys()))
p = d["result"]["positions"][0]
print("position keys:", list(p.keys()))
print(json.dumps(p, ensure_ascii=False, indent=1)[:1000])
