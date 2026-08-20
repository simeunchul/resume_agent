# profile/example

여기 있는 파일을 한 단계 위(`profile/`)로 복사한 뒤 본인 내용으로 채우면 됩니다.

```bash
cp profile/example/*.yaml profile/example/*.md profile/
rm profile/README.md          # 이 안내는 옮길 필요 없다
```

| 파일 | 무엇 | 누가 읽나 |
|---|---|---|
| `projects.yaml` | 프로젝트·경력 원본 (bullet 풀) + 헤더 인적사항 | compose · gap_analyze |
| `skills.yaml` | 스킬 칩 + 미경험 항목(점선칩) | compose · gap_analyze |
| `facts.yaml` | **검증된 수치의 단일 출처** + 금지 문자열 | fact_guard · compose |
| `rules.md` | 작성 규칙 — compose 프롬프트에 그대로 주입 | compose |
| `summary.md` | 지원자 배경 요약 — 적합도 게이트 입력 | fit_gate |
| `career_facts.md` | 경력 연차 사실 3줄 — 갭 분석 프롬프트에 주입 | gap_analyze |

`profile/` 의 실제 파일은 개인 정보라 `.gitignore` 에 걸려 있습니다. 커밋되지 않습니다.

주의 — `facts.yaml` 에 등록하지 않은 숫자는 이력서에 들어갈 수 없습니다.
새 수치가 생기면 여기부터 고치세요. 그러지 않으면 fact_guard 가 3회 재작성 후
PDF 생성을 거부합니다(fail-closed).
