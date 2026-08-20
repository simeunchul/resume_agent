import io, json, sys, copy
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from resume_agent.guards.fact_guard import FactGuard

g = FactGuard()
print(f"허용 수치 토큰 {len(g.allowed)}개 / 금지 패턴 {len(g.banned)}개\n")

slots = json.load(open("scripts/reference_slots.json", encoding="utf-8"))
print("=== 1. 정본(인피닉 이력서)은 통과해야 한다 ===")
r = g.check(slots)
print(r.report() if not r.ok else "  ✅ 통과")

print("\n=== 2. 금지 수치를 일부러 심으면 잡혀야 한다 ===")
bad = copy.deepcopy(slots)
bad["core"][2]["body"] = bad["core"][2]["body"].replace("74개 Airflow DAG", "92개 Airflow DAG")
bad["core"][1]["body"] += " 라벨 매핑을 고쳐 <b>0.0065 → 0.972</b>로 끌어올림"
bad["blocks"][1]["bullets"][3] = bad["blocks"][1]["bullets"][3].replace("bge-m3(1024차원)", "all-minilm(384d)")
bad["core"][0]["body"] += " 무효 데이터 <b>87%</b>를 걸러냄"
r = g.check(bad)
print(f"  위반 {len(r.violations)}건")
print(r.report())

print("\n=== 3. 역할 경계 위반 ===")
bad2 = copy.deepcopy(slots)
bad2["blocks"][2]["bullets"][0] = "추천 모델 아키텍처를 <b>혼자</b> 설계하고 학습시킴"
r = g.check(bad2)
print(r.report())

print("\n=== 4. 정직 표기 누락 ===")
bad3 = copy.deepcopy(slots)
bad3["not_yet_chips"] = []
bad3["honesty_note"] = "열심히 하겠습니다."
r = g.check(bad3)
print(r.report())
