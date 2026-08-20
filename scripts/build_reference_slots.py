"""인피닉 이력서를 슬롯 JSON 으로 역변환 — 렌더 파이프라인 회귀 기준."""
import io, json, sys, yaml
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

P = yaml.safe_load(io.open("profile/projects.yaml", encoding="utf-8"))
m, c = P["main_project"], P["career"]

def bl(block_id, idxs):
    b = next(x for x in m["blocks"] if x["id"] == block_id)
    return [" ".join(b["bullets"][i]["text"].split()) for i in idxs]

def tech(block_id):
    b = next(x for x in m["blocks"] if x["id"] == block_id)
    return ", ".join(b["tech"])

slots = {
    "company": "인피닉", "job_title": "AI Agent Engineer",
    "header": P["header"], "career_first": False, "show_overseas": False,
    "tagline": "에이전트를 <b>프레임워크 없이 직접 배선해 매일 돌게 만들고</b>, 그 답변 품질을 <b>지표로 관리해 온</b> 개발자",
    "core": [
        {"title": "AI 에이전트 시스템 설계·개발",
         "body": "매 배치 뒤 <b>53개 점검 항목</b>을 LLM이 <b>도구를 직접 호출</b>해 확인·판정하고 일간 보고서를 만드는 <b>운영 감사 에이전트를 혼자 구축</b>. 도구 관리를 <b>스키마·구현·라우팅 3계층으로 분리</b>해 도구 추가 시 코드 수정이 필요 없게 함"},
        {"title": "에이전트 답변 품질 평가 · 개선",
         "body": "출력 <b>3단 안전 게이트</b>로 거르고 통과 못 하면 재생성 없이 원본으로 되돌림. 생성 문장이 실제 근거를 언급하는지 대조하는 <b>그라운딩 검증</b>과 <b>충실도·근거성·컴플라이언스·가독성 가중합</b>으로 품질을 상시 추적 — <b>1건 0.63초 · 환각 0</b> 실측"},
        {"title": "워크플로우 · 데이터 가공 설계",
         "body": "전 구간을 <b>74개 Airflow DAG</b>로 오케스트레이션. Hive 수집을 <b>병렬(약 3배)</b>로 재설계하고 DuckDB SQL로 억 단위 거래를 집계. 후보 항목 <b>4,035개 전수 스캔</b> 후 700여 개로 큐레이션"},
        {"title": "동향 파악과 근거 기반 채택",
         "body": "경량 LLM을 태스크별로 벤치마크해 <b>탈락 근거까지 기록</b>(표본 12건 전부 환각, JSON 파싱 60%·0% 붕괴 등). 채택 직전이던 개선안도 결과가 좋게 나오자 <b>시드를 바꿔 재검증해 우연임을 밝히고 폐기</b>"},
    ],
    "main": {
        "org": m["org"], "emphasis": "", "period": m["period"],
        "participation": m["participation"], "team": m["team"],
        "env": "온프렘 폐쇄망 · 외부 API 호출 불가",
        "role_boundary": "<b>본인 단독</b> 운영 감사 에이전트 전체 ／ <b>본인 주도</b> LLM 응용 계층, RAG·검색, 품질 평가, 데이터 가공 ／ <b>팀 공동</b> 추천 모델 아키텍처·학습",
    },
    "blocks": [
        {"title": "AI 에이전트 시스템 설계·구축", "period": "2026.01 - 2026.06", "scope": "단독",
         "bullets": bl("agent_system", [0, 1, 2, 3]), "tech": tech("agent_system")},
        {"title": "에이전트 답변 품질 평가 · 개선", "period": "2026.01 - 2026.06", "scope": "단독",
         "bullets": bl("quality_eval", [0, 1, 2, 3]), "tech": tech("quality_eval")},
        {"title": "데이터 가공 · 워크플로우 · 서빙", "period": "2025.03 - 2026.06", "scope": "",
         "bullets": bl("data_serving", [0, 1]), "tech": tech("data_serving")},
    ],
    "career": {**{k: c[k] for k in ("org", "period", "type", "team", "exit")},
               "bullets": [" ".join(b["text"].split()) for b in c["bullets"]]},
    "side_projects": [{"title": s["title"], "meta": s["meta"],
                       "text": " ".join(s["text"].split()), "tech": s["tech"]}
                      for s in P["side_projects"]],
    "education": P["education"], "research": P["research"], "links": P["links"],
    "skill_groups": [
        {"label": "AI 에이전트 · LLM",
         "chips": ["에이전트 설계·구축", "Function Calling", "도구 스키마·라우팅 설계", "프롬프트 설계", "RAG",
                   "Vector DB(LanceDB)", "bge-m3 임베딩", "grounding 검증", "품질 게이트(fail-closed)",
                   "다중 투표 합의", "모델 벤치마크", "VLM(멀티모달)"]},
        {"label": "개발 · 서빙 · 워크플로우",
         "chips": ["Python", "PyTorch", "LightGBM", "지식증류", "Ollama", "멀티 백엔드 추상화", "FastAPI",
                   "Docker", "Airflow", "MLflow", "SQL · DuckDB", "TypeScript", "Scala"]},
    ],
    "not_yet_chips": ["LangChain · LangGraph (학습 중)", "모델 파인튜닝(LoRA 등)", "TensorFlow",
                      "Kubernetes 대규모 운영", "GCP · Azure"],
    "honesty_note": "정직하게 밝힙니다 — <b>LangChain·LangGraph로 서비스를 구축해 본 경험은 없습니다.</b> 폐쇄망이라 외부 의존을 늘리기 어려워, 그 프레임워크들이 담당하는 <b>도구 스키마 관리·라우팅·상태 전달·결과 합성을 직접 배선</b>했습니다. 그래서 프레임워크를 읽을 때 무엇을 대신해 주는지가 보이고, 제가 겪은 선택지 과부하 같은 문제는 프레임워크를 써도 동일하게 발생한다고 이해하고 있습니다. 현재 <b>LangChain 1.0 기준 예제로 같은 구조를 다시 구현하며 익히는 중</b>입니다.",
}
json.dump(slots, open("scripts/reference_slots.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("reference_slots.json 작성 완료")
print(f"  핵심역량 {len(slots['core'])} · 블록 {len(slots['blocks'])} · 기타 {len(slots['side_projects'])}")
