# resume_agent

채용 공고를 스스로 찾아 읽고, **검증된 사실만으로** 이력서를 다시 써서 PDF까지 뽑는 LangGraph 에이전트.

## 설치

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .       # ★ editable 설치
.venv\Scripts\python.exe -m playwright install chromium

copy .env.example .env                             # GOOGLE_API_KEY · RESUME_ROOT 채우기
copy profile\example\*.yaml profile\               # 본인 이력 데이터로 채우기
copy profile\example\*.md profile\
```

`pip install -e .` 를 해야 `import resume_agent` 가 되고 VSCode/Pylance 도 경로를 찾는다.
안 하면 에디터에 "가져오기를 확인할 수 없습니다" 노란 줄이 뜬다 (실행은 되지만 자동완성이 죽는다).

**`profile/` 이 이 프로젝트의 입력 전부다.** 개인 정보라서 git 에 올라가지 않는다 —
`profile/example/` 의 예시를 복사해 본인 내용으로 바꿔야 돌아간다. 무엇을 채우는지는
[profile/example/README.md](profile/example/README.md) 참고.

`.env` 의 `RESUME_ROOT` 가 산출물이 쌓일 폴더다. 비워 두면 프로젝트 안 `output/` 으로 떨어진다.
증명사진은 `RESUME_ROOT\공통_프로필_포트폴리오\photo.jpg` 에서 찾고, 없으면 사진 없이 렌더한다.

## 실행

```bash
run.bat                # 수집 → 적합도 게이트 → 이력서 생성 (기본 5건)
run.bat --limit 3      # 생성 상한 조정
run.bat --dry          # 수집·필터 결과만 보고 멈춤
run.bat --url <URL>    # 공고 URL 한 건만 처리 (잡코리아·링크드인 URL 도 여기로)
run.bat --jobkorea     # 잡코리아도 수집 (이미지 공고라 느리다)
run.bat --queue        # 지원 대기열만 다시 생성
```

⚠️ **`python run.py` 로 실행하지 말 것.** 전역 파이썬에는 이 패키지가 없어서 실패한다.
`run.bat` 은 어느 폴더에서 실행하든 이 프로젝트의 venv 파이썬을 쓴다.
(직접 부르려면 `.venv\Scripts\python.exe run.py ...`)

**지원 흐름**

1. `run.bat` 실행 → `이력서\_지원대기열.md` 를 연다 (마감 임박 순, 공고·PDF 링크)
2. 공고 열어 지원하고, 그 회사 폴더의 `공고.md` 에서 `- [ ] 지원함` → `- [x]` 로 바꾼다
3. `run.bat --queue` 로 대기열 갱신 (다음 실행 때 자동으로도 갱신됨)

산출물 → `{RESUME_ROOT}\{회사}_{직무}\`
- `{이름}_이력서.html` · `{이름}_이력서.pdf` · `photo.jpg`
  (이름은 `.env` 의 `RESUME_OWNER`, 없으면 `profile/projects.yaml` 의 `header.name`)
- `공고.md` — 공고 URL + JD 원문 + 요건별 판정 + 지원 기록 체크박스
  (공고는 마감되면 내려간다. 면접 준비 때 다시 봐야 하므로 원문을 남긴다)

지원 대기열 → `이력서\_지원대기열.md` (마감 임박 순, 공고·PDF 링크)
지원 이력 → `applications.jsonl` / 실행 요약 → `runs/{날짜}/summary.md`

---

## 그래프

```
collect ─→ dedupe ─→ prefilter ─→ (공고별)

  ingest ──(본문이 이미지)──→ screenshot ─→ VLM 판독 ─┐
     └──────────(텍스트)──────────────────────────────┤
                                                       ▼
                                                   parse_jd
                                                       │
                                                  fit_gate ──(미달)──→ 목록만 기록
                                                       │
                                                 gap_analyze
                                                       │
                                                  compose ◄────────┐
                                                       │           │
                                                fact_guard ──위반──┘ (최대 2회)
                                                       │
                                                  render ◄─────────┐
                                                       │           │
                                               verify_pages ──>2p──┤
                                                       │        trim (최대 3회)
                                                   finalize
```

되돌림 루프 두 개가 이 프로젝트의 핵심이고, 둘 다 **모델이 아니라 코드가 강제**한다.

## 설계에서 양보하지 않은 것

**1. LLM에게 HTML을 쓰게 하지 않는다**
템플릿은 Jinja2(`templates/resume.j2.html`)이고 LLM은 슬롯 JSON만 만든다.
HTML 전체를 맡기면 【고정】 구간과 CSS를 조용히 바꿔놓는다.

**2. 수치가 든 문장도 LLM이 쓰지 않는다**
프로젝트 bullet은 `profile/projects.yaml`의 풀에서 **인덱스로 고르기만** 한다 → 원문 그대로 복사된다.
LLM이 자유롭게 쓰는 건 한 줄 소개·핵심역량 4줄·블록 제목·그룹명·정직 표기뿐이다.

**3. 팩트 가드는 LLM 없이 결정적으로 돈다** (`guards/fact_guard.py`)
근거 코퍼스 자체가 오염돼 있다 — `gotothemoon_사례모음집.md`에 폐기된 `92개 DAG`·`0.0065→0.972`가 남아 있다.
그래서 `profile/facts.yaml`을 사실의 단일 출처로 두고 생성물 쪽에서 한 번 더 거른다.

- 숫자를 정규식으로 뽑아 허용 목록과 대조 → 없으면 위반
  (공고 원문에 있는 수치는 **인용**으로 허용 — "3년 이상 요건에 미달합니다"는 정당하다)
- 금지 문자열 매칭 (`87%` `0.0065` `92개` `all-minilm` `384d` `7.8B` …)
- **경력 연차 부풀리기 차단** — 정규 경력은 서버팀 **10개월**이고 우체국 16개월은 고용이 아니다.
  둘을 합쳐 "총 경력 2년", "3년차"라고 쓰면 허위 기재다. 문장 단위로 잡되 JD 요건 인용은 통과시킨다
- `"혼자/단독"`이 운영 감사 에이전트 밖에 붙었는지
- 점선칩 그룹·정직 표기 note 존재, `"정직하게 밝힙니다 —"` 시작구
- 3회째 실패하면 **PDF를 만들지 않고** 로그만 남긴다 (fail-closed)

**4. 기계적으로 판단할 수 있는 건 LLM에게 맡기지 않는다** (`nodes/fit_gate.py`)

적합도 게이트에서 처음엔 "요구 경력 하한이 N년 이상이면 결격"까지 LLM에게 시켰다.
결과: 하한 **1년·2년**짜리 공고까지 결격 처리했다 (2026-08-20). LLM이 *"경력이 부족하다"* 는
사실과 *"그래서 결격이다"* 라는 판정을 섞은 것이다.

지금은 역할을 쪼갰다.

| | 담당 | 하는 일 |
|---|---|---|
| **LLM** | 추출 | `min_years_required` 에 요구 연차의 **하한을 숫자로만** 담는다. 판정 금지 |
| **코드** | 판정 | `min_years_required >= MIN_YEARS_BLOCK` → 결격 (`config.py`, 기본 3) |

부수 효과로 **점수가 정확해졌다.** 예전엔 LLM이 연차 미달을 점수에도 반영해 이중으로 깎았는데
(크라우드웍스 88 → 지금 95), 이제 점수는 직무 적합도만 본다. "직무는 잘 맞는데 연차가 안 맞음"이
구분돼서 나온다.

LLM이 지시를 어기고 연차를 `blockers` 에 넣는 경우도 있어 코드가 정규식으로 걷어낸다 —
**판정을 두 곳에서 하면 반드시 어긋난다.**

기준을 바꾸려면 `config.MIN_YEARS_BLOCK` 만 고치면 된다 (3=좁게 / 5=중간 / 99=연차 무시).

**5. PDF는 Playwright가 아니라 Edge headless로 뽑는다**
기존 이력서 PDF가 전부 Edge 출력이라 렌더러를 바꾸면 폰트 메트릭이 달라져 2페이지 경계가 흔들린다.
과거 실패 원인 두 가지를 코드로 막았다 — ① 남은 msedge 프로세스 정리 ② `--user-data-dir` 사전 생성.

**6. 분량 초과 시 zoom을 건드리지 않는다**
`① 기타 프로젝트 → ② 블록 bullet(뒤에서부터) → ③ 핵심역량 축약` 순으로 **내용만** 덜어낸다.

## 소스 (2026-08-19 실측)

| 소스 | 목록 | 본문 | 판정 |
|---|---|---|---|
| 원티드 | static JSON | 텍스트 3,100~3,600자 | **채택** |
| 점핏 | static JSON | 텍스트 | **채택** (하이라이트 `<span>` 제거 필요) |
| 사람인 | 오픈API | — | 키 있으면 자동 활성 |
| 잡코리아 | 필터 불가 | **100% 이미지** (29K~51K px) | `--jobkorea` 옵션 |
| 링크드인 | — | — | 제외 (robots.txt가 자동 접근 금지 명시) |
| 잡플래닛 | 로그인 필요 | — | 제외 |
| 프로그래머스 | DNS 실패 | — | 제외 (도메인 개편) |

자세한 근거는 [docs_1단계_소스실측결과.md](docs_1단계_소스실측결과.md).

## 이미지 공고 판독

본문이 이미지라 드래그가 안 되는 공고는 **별도 OCR 엔진이 아니라 VLM**으로 읽는다.
한국어 공고 이미지에서 더 정확하고 표·박스 레이아웃도 같이 이해한다.

1. 파싱 결과가 빈약하면(담당업무 또는 자격요건 < 2건) 이미지 경로로 재시도 — 휴리스틱이 아니라 **결과 기반** 판단
2. 지연 로딩 이미지를 스크롤로 강제 로드 (안 하면 빈 화면을 찍는다)
3. 2,000px씩 최대 8조각으로 잘라 VLM에 전달 (`clip`은 `full_page=True`와 함께 써야 한다)

실측: 잡코리아 이미지 공고에서 담당업무 1건 → **15건**, 자격요건 쓰레기 2건 → 실제 5건.

## 모델 (2026-08-19 실측으로 고정)

목록에 있다고 다 쓸 수 있는 게 아니다. 실제로 호출해 보고 골랐다.

| 모델 | 결과 |
|---|---|
| `gemini-3.5-flash` | OK 3.5s — **1순위** |
| `gemini-2.5-flash` | OK 5.7s — 2순위 |
| `gemini-3.5-flash-lite` | OK 0.9s — 3순위 |
| `gemini-3.7-flash` | 429 (무료 티어 쿼터) → 제외 |
| `gemini-3.6-flash` | 503, 응답까지 **112초** → 제외 |
| `gemini-2.5-pro` | 404 (이 키로 접근 불가) → 제외 |

429는 기다려도 안 풀리므로 재시도 없이 즉시 다음 모델로 강등한다.
이 체인 교체로 공고 1건당 **525초 → 80초**가 됐다.

## 구조

```
run.py                       배치 실행 진입점
profile/                     ★ 사실의 단일 출처 (개인 정보 — git 에 올라가지 않는다)
  facts.yaml                   검증 수치 + 근거 + 금지 목록
  projects.yaml                프로젝트·경력 원본 (bullet 풀) + 헤더 인적사항
  skills.yaml                  스킬 칩 + 미경험 항목
  rules.md                     작성 규칙 (compose 프롬프트에 주입)
  summary.md                   지원자 배경 요약 (fit_gate 입력)
  career_facts.md              경력 연차 사실 (gap_analyze 프롬프트에 주입)
  example/                     ↑ 위 6개의 빈 양식. 복사해서 채운다
templates/resume.j2.html     원본 템플릿의 Jinja2 사본 (CSS 동일)
src/resume_agent/
  graph.py  state.py  llm.py  schemas.py  config.py
  sources/    wanted · jumpit · saramin · collect
  nodes/      ingest · parse_jd · fit_gate · gap_analyze · compose · finalize
  render/     jinja · edge_pdf · page_count · trim
  guards/     fact_guard
```

## 자동 입사지원은 하지 않는다

기술적 가능성 문제가 아니라 **두 사이트가 명시적으로 금지**한다.

- **원티드 이용약관 제7항** — "회원"은 "회사"의 사전 허락 없이 **자동화된 수단(매크로 프로그램,
  로봇(봇), 스파이더, 스크래퍼 등)을 이용하여** … **서비스에 로그인을 시도 또는 로그인하거나**,
  각 "사이트"에 게시물을 게재하거나 … 해서는 안 된다
- **점핏 robots.txt** — `Disallow: /resumes /resume/ /myjumpit /applications-status/ /account`

실질적 위험도 크다. 지원은 **되돌릴 수 없고**(취소해도 기업에는 이미 노출), 잘못 나가거나
중복 지원되면 회복이 안 되며, 봇으로 걸리면 구직 계정 자체가 막힌다.

대신 `_지원대기열.md` 로 "공고 열기 → PDF 첨부" 를 최소 클릭으로 끝내게 돕는다.
지원했으면 그 폴더 `공고.md` 의 `- [ ] 지원함` 을 `- [x]` 로 바꾸면 대기열에서 빠진다.
(참고: 표본 48건 전부 원티드 내부 지원이라 회사별 폼을 따로 상대할 일은 없다)

## 경력 사실 — 절대 흔들리면 안 되는 것

**정규 고용 기간과 프로젝트 참여 기간을 합산하면 허위 기재다.** 이 프로젝트가 가장 신경 쓴 지점이고,
LLM 은 놔두면 반드시 둘을 더해 "총 경력 N년"이라고 쓴다.

사실은 `profile/` 한 곳에만 둔다 — `summary.md`(적합도 게이트) · `career_facts.md`(갭 분석) ·
`rules.md`(작성 규칙). 프롬프트에는 파일 내용이 주입될 뿐 코드에 박혀 있지 않다.
마지막 방어는 `fact_guard._check_career` 가 결정적으로 한다.

⚠️ `fact_guard` 의 경력 검사 규칙(`10개월`·`16개월` 같은 리터럴)은 아직 작성자 기준으로 하드코딩돼 있다.
다른 사람이 쓰려면 `guards/fact_guard.py` 의 `_check_career` 를 본인 기간에 맞게 고쳐야 한다.

## 유지보수 시 주의

- **`profile/facts.yaml`에 없는 수치는 이력서에 못 들어간다.** 새 근거가 생기면 여기부터 고친다.
- `gotothemoon_사례모음집.md`를 근거 원본으로 쓰지 말 것 — 폐기된 수치가 섞여 있다.
- 이 프로젝트가 완성되면 `skills.yaml`의 `not_yet`에서 **LangChain·LangGraph 항목을 빼고**
  `side_projects`에 올린다. 지금 이력서 점선칩에 "LangChain · LangGraph (학습 중)"이 박혀 있다.
