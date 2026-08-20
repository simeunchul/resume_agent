import io, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from resume_agent.sources.base import JobCandidate
from resume_agent.graph import run_one

c = JobCandidate(source="wanted", source_id="381470",
                 url="https://www.wanted.co.kr/wd/381470",
                 title="AI Agent 엔지니어", company="크라우드웍스")
print(f"▶ {c.company} / {c.title}\n  {c.url}")
t0 = time.time()
st = run_one(c)
print(f"\n결과: {st.get('outcome')} ({time.time()-t0:.0f}s)")
if st.get("outcome") == "생성":
    print(f"  폴더: {st.get('out_dir')}")
    print(f"  페이지: {st.get('pages')} | 덜어냄: {st.get('trims')}")
    s = st["slots"]
    print(f"\n  한 줄 소개: {s['tagline']}")
    print("  핵심역량:")
    for x in s["core"]:
        print(f"    · {x['title']} — {x['body'][:110]}…")
    print(f"  블록: {[b['title'] for b in s['blocks']]}")
    print(f"  점선칩: {s['not_yet_chips']}")
    print(f"\n  정직 표기: {s['honesty_note'][:400]}")
else:
    print(f"  사유: {st.get('reason')}")
