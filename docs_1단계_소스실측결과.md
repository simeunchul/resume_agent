# 1단계 — 공고 소스 접근성 실측 결과 (2026-08-19)

실제로 호출해서 확인한 결과. 계획서의 "검색 경유 보조 경로"는 **불필요해져 삭제**한다.

## 확정 — 주력 2소스 (실측 후 잡코리아 제외)

| 소스 | 목록 | 본문 | 판정 |
|---|---|---|---|
| **원티드** | ✅ static JSON | ✅ 텍스트 3,100~3,600자 | **채택** |
| **점핏** | ✅ static JSON | ✅ 텍스트 729자 | **채택** |
| 잡코리아 | ⚠️ 필터 불가 | ❌ 100% 이미지 | **자동수집 제외 · 옵션** |

### 실측 수집량 (2026-08-19, 키워드 8개)
```
소스별 원시: {'wanted': 96, 'jumpit': 128}
원시 224건 → 중복제거 136건 → 신규 136건 → 관련 111건
```
원티드·점핏 본문에서 `주요업무`·`자격요건`·`우대사항`이 모두 텍스트로 추출된다. 공급량이 충분해 잡코리아 없이 진행 가능.

### 원티드
- 엔드포인트: `https://www.wanted.co.kr/api/chaos/search/v1/results?query={kw}&tab=position`
- 응답: `positions.total_count`, `positions.data[]` — `id / position / company.name / due_time / employment_type / category_tag / address`
- 공고 URL: `https://www.wanted.co.kr/wd/{id}`
- 실측 건수: `AI 엔지니어` 125 · `데이터 엔지니어` 77 · `LLM` 59 · `MLOps 엔지니어` 7
- ⚠️ `limit` 파라미터가 무시되고 12건씩 반환됨 → 페이지네이션 파라미터 확인 필요
- ❌ `api/v4/categories` 는 404. `tag_type_ids` 추정값은 엉뚱한 결과 → **키워드 검색만 사용**

### 점핏
- 엔드포인트: `https://api.jumpit.co.kr/api/positions?sort=reg_dt&highlight=false&page={n}&keyword={kw}`
- 응답: `result.totalCount`, `result.positions[]` — `id / title / companyName / jobCategory / techStacks / minCareer / maxCareer / closedAt / locations`
- 공고 URL: `https://jumpit.saramin.co.kr/position/{id}`
- ⚠️ `highlight=false` 를 줘도 `<span>` 하이라이트 태그가 title·techStacks 에 섞임 → **태그 제거 필요**
- ⚠️ 키워드 정확도 낮음 (`MLOps` 검색에 자율주행 알고리즘 개발자가 나옴) → **로컬 재필터 필수**

### 잡코리아 — 자동수집에서 제외 (옵션으로만 유지)

**제외 사유 (실측):**
1. 🔴 **상세요강이 100% 이미지.** 본문은 별도 iframe `/Recruit/GI_Read_Comt_Ifrm?Gno={id}` 에 있는데 **텍스트 0자**, 큰 이미지 2~4장뿐. 총 높이가 **29,234px · 51,116px** 로 VLM 에 통째로 못 넣고 분할해야 하며 호출 비용이 크다
2. 🔴 **직무 카테고리 필터 불가.** `dutyCtgr` 코드가 static HTML 에도 JS 렌더 후에도 안 나온다. 임의로 넣은 `dutyCtgr=10031` 의 실제 내용은 영업관리사·홀서비스·영양사 등 **AI/데이터와 무관한 잡탕**
3. 본문 페이지 자체의 텍스트에는 `지원자격`(경력·학력·스킬·우대조건)과 마감일만 있고 `담당업무`·`자격요건` 은 없다

→ 원티드·점핏만으로 관련 공고 111건이 확보되므로 잡코리아는 **기본 꺼짐 옵션**(`use_jobkorea=True`)으로만 남긴다. 사용자가 잡코리아 URL 을 직접 주는 경우는 이미지 판독 경로로 처리한다.

### 잡코리아 robots.txt — 켤 경우 반드시 지킬 것
robots.txt(2026-04-01)가 AI/LLM 크롤러를 `Disallow: /` 하면서 아래를 **명시적으로 Allow** 한다:
```
Allow: /recruit/joblist      ← 목록. 사용함
Allow: /Recruit/GI_Read      ← 공고 본문. 사용함
Allow: /recruit/ai-jobs
```
반대로 General Rules 에서 아래는 **Disallow** —  접근이 되더라도 쓰지 않는다:
```
Disallow: /Search/?stext=            ← 키워드 검색. 사용 금지
Disallow: /recruit/ai-jobs/search
```
- 목록: `/recruit/joblist?menucode=duty&dutyCtgr={code}` → HTML 에서 `/Recruit/GI_Read/(\d+)` 정규식으로 ID 추출 (실측 144건, 캡차·차단 없음)
- 본문: `https://www.jobkorea.co.kr/Recruit/GI_Read/{id}`
- 🔴 **본문은 static HTTP 로 못 읽는다.** `자격요건`·`우대사항`·`담당업무` 문자열이 HTML 에 전혀 없고 iframe 0개 → **JS 렌더링. Playwright 필수**
- `dutyCtgr` 코드 목록도 static HTML 에 없음 → Playwright 로 한 번 수집해 상수로 고정할 것

## 제외 확정

| 소스 | 사유 |
|---|---|
| **링크드인** | robots.txt 에 "use of robots or other automated means to access LinkedIn without the express permission is strictly prohibited" 명시. 쓰지 않는다 |
| **잡플래닛** | 목록 조회에 로그인 필요. 공고 상당수가 원티드·사람인 재게시 |
| **프로그래머스** | `career.programmers.co.kr` DNS 해석 실패, `programmers.co.kr/job` 404. 도메인 개편된 것으로 보임 |

## 보류 — 사람인 오픈API
- 엔드포인트 정상 동작. 무키 호출 시 `{"code":2,"message":"사용 불가능한 access-key 입니다."}`
- developer.saramin.co.kr 에서 **무료 키 발급 필요 (사용자 액션)**
- 키가 `.env` 에 있으면 켜지고 없으면 건너뛰는 구조로 구현 → 지금은 없어도 진행 가능

## 검색 경유 보조 경로 — 삭제
잡코리아가 직접 열리므로 검색을 경유할 이유가 사라졌고, 링크드인은 검색을 경유해도 본문이 로그인 벽 + ToS 위반이라 어차피 못 쓴다. 남는 이득이 없어 설계에서 제거한다.
