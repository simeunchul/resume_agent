import io, sys, json, copy
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from resume_agent.guards.fact_guard import FactGuard
g = FactGuard()

CASES = [
    ("총 경력 2년 3개월의 AI 엔지니어입니다.", True),
    ("AI 엔지니어 3년차로서 에이전트를 설계해 왔습니다.", True),
    ("2년 이상의 실무 경험을 바탕으로 파이프라인을 구축했습니다.", True),
    ("3년 이상의 소프트웨어 엔지니어링 경력을 요구하는 요건에 대해, 정규 경력은 서버팀 10개월입니다.", False),
    ("공고가 요구하는 5년 경력 기준에는 미달합니다.", False),
    ("1,200만 고객 프로젝트는 정규 고용이 아닌 현장 프로젝트형 참여이며, 정규 경력은 서버팀 10개월입니다.", False),
    ("전 구간을 74개 Airflow DAG로 오케스트레이션했습니다.", False),
    ("2024년 2월부터 서버팀에서 근무했습니다.", False),
]
print("=== 경력 연차 검사 ===")
ok = 0
for text, should_flag in CASES:
    vs = g._check_career(text, "test")
    flagged = bool(vs)
    mark = "✅" if flagged == should_flag else "❌"
    if flagged == should_flag: ok += 1
    print(f"  {mark} {'차단' if flagged else '통과':4s} (기대={'차단' if should_flag else '통과'}) {text[:56]}")
    for v in vs: print(f"        └ {v}")
print(f"\n  {ok}/{len(CASES)} 통과")

print("\n=== 정본(인피닉)은 여전히 통과해야 한다 ===")
slots = json.load(open("scripts/reference_slots.json", encoding="utf-8"))
r = g.check(slots)
print("  ✅ 통과" if r.ok else r.report())
