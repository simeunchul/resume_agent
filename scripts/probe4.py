import json, ssl, urllib.error, urllib.parse, urllib.request, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CTX=ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE
def get(u,h=None,t=20):
    r=urllib.request.Request(u,headers={"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9",**(h or {})})
    try:
        with urllib.request.urlopen(r,timeout=t,context=CTX) as x: return x.status,x.read()
    except urllib.error.HTTPError as e: return e.code,e.read()[:500]
    except Exception as e: return None,f"{type(e).__name__}: {e}".encode()

print("### 원티드 chaos search -> positions.data 정확히 보기")
for kw in ["AI 엔지니어","MLOps 엔지니어","데이터 엔지니어","LLM"]:
    st,b=get("https://www.wanted.co.kr/api/chaos/search/v1/results?query="+urllib.parse.quote(kw)+"&tab=position&limit=8")
    if st!=200: print(f"[{kw}] 실패 {st}"); continue
    d=json.loads(b)
    pos=(d.get("positions") or {}).get("data") or []
    tot=(d.get("positions") or {}).get("total_count")
    print(f"[{kw}] positions total={tot} 반환={len(pos)}")
    if pos:
        print(f"    keys={list(pos[0].keys())}")
        for it in pos[:4]:
            c=it.get("company") or {}
            print(f"    - id={it.get('id')} | {it.get('position')} | {c.get('name') if isinstance(c,dict) else c} | due={it.get('due_time')}")
    print("-"*100)

print("### 원티드 v4 jobs 에 직군 필터 붙여보기 (tag_type_ids)")
for tid,label in [("518","개발 전체(추정)"),("872","데이터(추정)"),("677","AI/ML(추정)")]:
    st,b=get(f"https://www.wanted.co.kr/api/v4/jobs?country=kr&tag_type_ids={tid}&job_sort=job.latest_order&locations=all&years=-1&limit=5&offset=0")
    if st==200:
        d=json.loads(b); arr=d.get("data",[])
        print(f"  tag_type_ids={tid} ({label}) -> {len(arr)}건")
        for it in arr[:3]:
            print(f"      {it.get('position')} | {(it.get('company') or {}).get('name')}")
    else: print(f"  tag_type_ids={tid} 실패 {st}")

print("="*100)
print("### 점핏 키워드 검색 파라미터 확인")
for kw in ["AI","MLOps","데이터"]:
    st,b=get("https://api.jumpit.co.kr/api/positions?sort=reg_dt&highlight=false&page=1&keyword="+urllib.parse.quote(kw))
    if st==200:
        d=json.loads(b); r=d.get("result",{})
        print(f"[{kw}] totalCount={r.get('totalCount')} keyword={r.get('keyword')} 반환={len(r.get('positions',[]))}")
        for p in r.get("positions",[])[:3]:
            print(f"    - {p.get('title')} | {p.get('companyName')} | {p.get('jobCategory')} | {p.get('techStacks')}")
    else: print(f"[{kw}] 실패 {st}")
