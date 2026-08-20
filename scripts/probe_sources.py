"""1단계: 채용 공고 소스 접근성 실측. stdlib만 사용."""
import json, ssl, sys, urllib.error, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def get(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/plain, */*", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400]
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".encode()


def probe(name, url, headers=None, dig=None):
    st, body = get(url, headers)
    line = f"[{name}] status={st} bytes={len(body)}"
    if st == 200:
        try:
            data = json.loads(body)
            n, sample = dig(data) if dig else (None, None)
            line += f" | JSON ok | count={n}"
            if sample:
                line += f"\n    sample: {json.dumps(sample, ensure_ascii=False)[:300]}"
        except Exception as e:
            line += f" | JSON parse fail: {e} | head={body[:150]}"
    else:
        line += f" | {body[:200]}"
    print(line, flush=True)
    print("-" * 100, flush=True)


print("=" * 100)
print("원티드 (Wanted)")
print("=" * 100)
probe("wanted v4 jobs",
      "https://www.wanted.co.kr/api/v4/jobs?country=kr&job_sort=job.latest_order&locations=all&years=-1&limit=20&offset=0",
      dig=lambda d: (len(d.get("data", [])), (d.get("data") or [{}])[0]))
probe("wanted search",
      "https://www.wanted.co.kr/api/chaos/search/v1/results?query=" + urllib.parse.quote("AI 엔지니어") + "&tab=position&limit=10",
      dig=lambda d: (len(json.dumps(d)), None))

print("=" * 100)
print("점핏 (Jumpit)")
print("=" * 100)
probe("jumpit positions",
      "https://api.jumpit.co.kr/api/positions?sort=reg_dt&highlight=false&page=1",
      dig=lambda d: (len((d.get("result") or {}).get("positions", [])), ((d.get("result") or {}).get("positions") or [{}])[0]))

print("=" * 100)
print("프로그래머스 커리어")
print("=" * 100)
probe("programmers",
      "https://career.programmers.co.kr/api/job_positions?page=1&order=recent",
      dig=lambda d: (len(d.get("jobPositions", [])), (d.get("jobPositions") or [{}])[0]))

print("=" * 100)
print("사람인 오픈API (키 없이 호출 시 응답 형태 확인)")
print("=" * 100)
probe("saramin openapi",
      "https://oapi.saramin.co.kr/job-search?access-key=TEST&keywords=" + urllib.parse.quote("AI") + "&count=5")

print("=" * 100)
print("잡코리아 / 링크드인 (직접 접근 가능 여부만 확인)")
print("=" * 100)
for nm, u in [("jobkorea robots", "https://www.jobkorea.co.kr/robots.txt"),
              ("linkedin robots", "https://www.linkedin.com/robots.txt")]:
    st, body = get(u)
    txt = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)
    print(f"[{nm}] status={st}")
    print("\n".join("    " + l for l in txt.splitlines()[:25]))
    print("-" * 100)
