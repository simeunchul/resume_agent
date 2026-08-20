import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from resume_agent.nodes.ingest import ingest
ing = ingest("https://www.jobkorea.co.kr/Recruit/GI_Read/49517249", force_image=True)
print(f"mode={ing.mode} text={len(ing.text)} images={len(ing.images)}")
print(f"error={ing.error!r}")
for i, b in enumerate(ing.images):
    print(f"  slice{i}: {len(b):,} bytes")
