import io, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from resume_agent.nodes.ingest import ingest
from resume_agent.nodes.parse_jd import parse_jd

TARGETS = [
    ("원티드(텍스트)", "https://www.wanted.co.kr/wd/381470"),
    ("점핏(텍스트)",   "https://jumpit.saramin.co.kr/position/54787941"),
    ("잡코리아(이미지)", "https://www.jobkorea.co.kr/Recruit/GI_Read/49517249"),
]
for label, url in TARGETS:
    t0 = time.time()
    ing = ingest(url)
    print(f"\n{'='*90}\n[{label}] {url}")
    print(f"  ingest: mode={ing.mode} text={len(ing.text):,}자 images={len(ing.images)}장 err={ing.error or '-'} ({time.time()-t0:.1f}s)")
    if not ing.ok:
        continue
    t1 = time.time()
    jd = parse_jd(ing)
    if jd is None:
        print("  parse 실패"); continue
    print(f"  parse: {time.time()-t1:.1f}s")
    print(f"  회사={jd.company} | 직무={jd.job_title} | 고용={jd.employment_type} | 마감={jd.deadline} | 경력={jd.experience_level}")
    print(f"  담당업무 {len(jd.responsibilities)} / 자격요건 {len(jd.requirements)} / 우대 {len(jd.preferred)} / 스택 {len(jd.tech_stack)}")
    for k, arr in (("담당업무", jd.responsibilities), ("자격요건", jd.requirements), ("우대사항", jd.preferred)):
        for x in arr[:3]:
            print(f"    [{k}] {x[:88]}")
