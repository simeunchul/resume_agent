import json, re, ssl, urllib.error, urllib.parse, urllib.request, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CTX=ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE
def get(u,h=None,t=20):
    r=urllib.request.Request(u,headers={"User-Agent":UA,"Accept-Language":"ko-KR,ko;q=0.9",**(h or {})})
    try:
        with urllib.request.urlopen(r,timeout=t,context=CTX) as x: return x.status,x.read()
    except urllib.error.HTTPError as e: return e.code,e.read()[:500]
    except Exception as e: return None,f"{type(e).__name__}: {e}".encode()

print("### A. 원티드 직군(카테고리) 목록")
st,b=get("https://www.wanted.co.kr/api/v4/categories?country=kr")
if st==200:
    d=json.loads(b)
    def walk(node,depth=0):
        for c in node:
            nm=c.get("title") or c.get("name"); cid=c.get("id")
            if any(k in str(nm) for k in ["개발","데이터","AI","엔지니어","머신","인공"]):
                print(f"{'  '*depth}id={cid} {nm}")
            for key in ("sub","children","tags"):
                if c.get(key): walk(c[key],depth+1)
    top=d.get("data") or d
    walk(top if isinstance(top,list) else [top])
else: print("  실패",st,b[:200])
print("="*100)

print("### B. 원티드 키워드 검색으로 AI 공고 뽑기")
for kw in ["AI 엔지니어","MLOps","데이터 엔지니어"]:
    st,b=get("https://www.wanted.co.kr/api/chaos/search/v1/results?query="+urllib.parse.quote(kw)+"&tab=position&limit=5")
    if st==200:
        d=json.loads(b)
        # 구조 탐색
        def find_positions(o,path=""):
            out=[]
            if isinstance(o,dict):
                for k,v in o.items():
                    if k in ("position_list","positions","data","results") and isinstance(v,list) and v and isinstance(v[0],dict):
                        out.append((path+"."+k,v))
                    out+=find_positions(v,path+"."+k)
            elif isinstance(o,list):
                for i,v in enumerate(o[:2]): out+=find_positions(v,f"{path}[{i}]")
            return out
        hits=find_positions(d)
        print(f"[{kw}] 후보경로={[p for p,_ in hits][:5]}")
        if hits:
            p,arr=hits[0]
            print(f"    keys={list(arr[0].keys())[:14]}")
            for it in arr[:3]:
                print(f"    - id={it.get('id')} | {it.get('position') or it.get('name') or it.get('title')} | {(it.get('company') or {}).get('name') if isinstance(it.get('company'),dict) else it.get('company_name')}")
    else: print(f"[{kw}] 실패 {st}")
print("="*100)

print("### C. 잡코리아 dutyCtgr 코드 찾기 (joblist 페이지에서 추출)")
st,b=get("https://www.jobkorea.co.kr/recruit/joblist?menucode=duty")
if st==200:
    h=b.decode("utf-8","replace")
    pairs=re.findall(r'dutyCtgr=(\d+)[^>]*>\s*([^<]{2,30})</a>',h)
    seen=set()
    for code,name in pairs:
        name=name.strip()
        if code in seen: continue
        seen.add(code)
        if any(k in name for k in ["AI","인공지능","데이터","머신","빅데이터","분석","개발","엔지니어","DBA","서버"]):
            print(f"  dutyCtgr={code}  {name}")
    print(f"  (전체 코드 {len(seen)}개 발견)")
else: print("  실패",st)
print("="*100)

print("### D. 잡코리아 공고 본문(GI_Read) 실제 읽기")
st,b=get("https://www.jobkorea.co.kr/Recruit/GI_Read/49074852")
print(f"status={st} bytes={len(b)}")
if st==200:
    h=b.decode("utf-8","replace")
    title=re.search(r'<title>(.*?)</title>',h,re.S)
    print("  title:",title.group(1).strip()[:120] if title else None)
    # 본문 텍스트 존재 여부
    for kw in ["자격요건","우대사항","담당업무","주요업무","모집부문","경력"]:
        print(f"  '{kw}' 포함: {kw in h}")
    print(f"  iframe(본문 별도로드) 개수: {len(re.findall(r'<iframe', h))}")
    ifr=re.findall(r'<iframe[^>]+src=[\"\']([^\"\']+)[\"\']',h)
    print(f"  iframe src 샘플: {ifr[:3]}")
    imgs=len(re.findall(r'<img',h))
    print(f"  img 태그 수: {imgs} (이미지 공고 판별 참고)")
