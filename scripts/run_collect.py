import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from resume_agent.sources.collect import collect_all
from resume_agent.config import SEARCH_KEYWORDS

print("키워드:", SEARCH_KEYWORDS)
r = collect_all()
print(f"\n소스별 원시 수집: {r['per_source']}")
print(f"원시 {r['raw']}건 → 중복제거 {r['unique']}건 → 신규 {r['fresh']}건 → 관련 {len(r['relevant'])}건\n")
for c in r["relevant"][:30]:
    due = (c.due or "상시")[:10]
    print(f"  [{c.source:7s}] {c.title[:52]:52s} | {c.company[:16]:16s} | ~{due}")
print(f"\n... 총 {len(r['relevant'])}건")
