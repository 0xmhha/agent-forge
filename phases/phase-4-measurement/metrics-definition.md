# Metrics Definition

## 핵심 메트릭 선정

README의 전체 메트릭 중 초기 수집에 집중할 핵심 메트릭을 선정한다.
모든 것을 측정하려 하면 측정 자체가 오버헤드가 된다. 최소한으로 시작한다.

---

## Tier 1: 필수 메트릭 (매 세션 수집)

모든 세션에서 반드시 수집하는 메트릭. 수집 비용이 낮아야 한다.

### M1: Total Tokens (총 토큰)

| 항목 | 값 |
|------|-----|
| 단위 | tokens |
| 수집 시점 | 세션 종료 |
| 수집 방법 | ccusage 또는 세션 로그에서 자동 추출 |
| 분해 | input_tokens, output_tokens, cache_read, cache_create |

총 토큰은 비용의 직접적 지표. 모든 비교의 기준선.

### M2: Workflow Tier (워크플로우 단계)

| 항목 | 값 |
|------|-----|
| 단위 | enum: micro, standard, full |
| 수집 시점 | 세션 시작 |
| 수집 방법 | 수동 기록 |

작업 복잡도와 토큰 소비의 상관관계 분석에 필수.

### M3: Files Changed (변경 파일 수)

| 항목 | 값 |
|------|-----|
| 단위 | integer |
| 수집 시점 | 세션 종료 |
| 수집 방법 | git diff --stat 또는 수동 기록 |

토큰/파일 효율성 계산의 분모.

### M4: QR Iterations (QR 반복 횟수)

| 항목 | 값 |
|------|-----|
| 단위 | array of integers (마일스톤별) |
| 수집 시점 | 각 QR 완료 |
| 수집 방법 | 수동 기록 |
| 해당 없음 | Micro 워크플로우 (QR 없음) |

QR 게이트의 비용 대비 효과를 판단하는 핵심 지표.

### M5: Rework Count (재작업 횟수)

| 항목 | 값 |
|------|-----|
| 단위 | integer |
| 수집 시점 | 세션 종료 |
| 수집 방법 | 같은 파일을 2회 이상 수정한 횟수 |

품질 문제의 간접 지표. QR 게이트가 재작업을 줄이는지 확인.

---

## Tier 2: 선택 메트릭 (분석 필요 시 수집)

특정 질문에 답하기 위해 필요할 때만 수집.

### M6: QR MUST Findings (QR MUST 발견 건수)

QR에서 MUST 심각도로 보고된 발견 건수. QR의 실질적 기여도를 측정.

### M7: Model Distribution (모델 분포)

세션 내 Haiku/Sonnet/Opus 사용 비율. 비용 효율성 분석에 사용.

### M8: Domain Profile (적용된 도메인 프로필)

어떤 프로필로 작업했는지. 도메인별 비교 분석에 사용.

### M9: Context Tokens (컨텍스트 토큰)

델타 로그/롤링 요약으로 주입된 토큰 수. 컨텍스트 관리의 오버헤드 측정.

### M10: Milestone Count (마일스톤 수)

Full 워크플로우에서 총 마일스톤 수. 토큰/마일스톤 효율성 계산.

---

## 수집 형식

### 세션 로그 (JSON)

```json
{
  "session_id": "2026-03-15-auth-jwt",
  "date": "2026-03-15",
  "project": "backend-api",
  "workflow_tier": "standard",
  "domain_profile": "fintech",
  "milestones": 3,
  "files_changed": 7,
  "qr_iterations": [1, 2, 1],
  "rework_count": 2,
  "tokens": {
    "total": 152000,
    "input": 98000,
    "output": 54000,
    "cache_read": 45000,
    "cache_create": 12000
  },
  "duration_minutes": 45,
  "notes": "M2에서 Temporal 위반 발견, QR 2회 반복"
}
```

### 파일 저장 위치

```
phases/phase-4-measurement/
├── data/
│   ├── sessions/           세션별 JSON 파일
│   │   ├── 2026-03-15-auth-jwt.json
│   │   └── 2026-03-16-payment-api.json
│   └── aggregated/         집계 데이터
│       └── weekly-summary.json
└── templates/
    └── session-log.json    빈 템플릿
```

---

## 파생 메트릭 (수집 데이터에서 계산)

| 파생 메트릭 | 계산식 | 용도 |
|-------------|--------|------|
| 토큰/파일 | total_tokens / files_changed | 파일 단위 비용 효율성 |
| 토큰/마일스톤 | total_tokens / milestones | 마일스톤 단위 비용 |
| QR 비용 비율 | (QR 단계 토큰) / total_tokens | QR 오버헤드 측정 |
| 첫 시도 통과율 | (iter=1 마일스톤 수) / 전체 마일스톤 | QR 효과성 |
| 캐시 효율 | cache_read / (input - cache_read) | 캐시 활용도 |
| 재작업률 | rework_count / files_changed | 품질 문제 비율 |
