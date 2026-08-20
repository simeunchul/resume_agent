import io, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from resume_agent.nodes.parse_jd import parse_jd_with_fallback
t0=time.time()
jd, ing = parse_jd_with_fallback("https://www.jobkorea.co.kr/Recruit/GI_Read/49517249")
print(f"\n[잡코리아 이미지형] mode={ing.mode} images={len(ing.images)}장 ({time.time()-t0:.0f}s)")
if jd:
    print(f"  회사={jd.company} | 직무={jd.job_title}")
    print(f"  담당업무 {len(jd.responsibilities)} / 자격요건 {len(jd.requirements)} / 우대 {len(jd.preferred)}")
    for k, arr in (("담당", jd.responsibilities), ("자격", jd.requirements), ("우대", jd.preferred)):
        for x in arr[:5]: print(f"    [{k}] {x[:95]}")
