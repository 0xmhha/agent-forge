---
name: milestone
description: |
  마일스톤 완료 워크플로우를 일괄 실행한다. QR → delta-log → 토큰 기록 → 커밋을 순서대로 수행.
  /milestone로 호출하면 모든 완료 절차를 자동화한다.
trigger-keywords: milestone, 마일스톤, 완료
user-invocable: true
---

## Instructions

마일스톤 완료 시 아래 절차를 순서대로 실행한다.

### Step 1: Tier 확인

현재 설정된 Tier를 확인한다:

```bash
!`cat /tmp/agent-forge-tier 2>/dev/null || echo "unknown"`
```

Tier가 설정되지 않았으면 /complexity를 먼저 실행하라고 안내한다.

### Step 2: QR 게이트 (Micro 제외)

Tier가 micro가 아니면 /qr-gate를 실행한다.
QR 결과가 NEEDS_CHANGES이면 수정 후 재실행.
PASS 또는 PASS_WITH_CONCERNS가 될 때까지 반복.

### Step 3: delta-log 생성

/delta-log를 실행하여 delta-log 엔트리와 rolling-summary를 생성/갱신한다.

### Step 4: 토큰 사용량 기록

token-monitor-mcp가 사용 가능하면 세션 토큰 데이터를 수집한다:
- `token_session_list`로 현재 세션 확인
- `token_session_export` (agent-forge 포맷)로 토큰 데이터 추출
- `phases/phase-4-measurement/data/sessions/` 에 session-log 저장

token-monitor가 사용 불가하면 이 단계를 건너뛰고 안내한다.

### Step 5: 커밋

모든 변경 사항 (코드 + delta-log + session-log)을 커밋한다.
커밋 규칙: 영어 conventional commits, Co-Author 금지.

### Step 6: 방법론 관찰

이번 마일스톤에서 방법론 적용 과정에서 발견된 개선점이 있으면 기록한다.
개선점이 있으면 `delta-logs/methodology-observations-M{N}.md`에 저장.

### 출력 요약

```
## Milestone M{N} 완료
- Tier: {Micro|Standard|Full}
- QR: {PASS|PASS_WITH_CONCERNS} (iter {N})
- Delta log: delta-logs/M{N}-{slug}.json
- Tokens: {total} (${cost_usd})
- Commit: {hash}
- 방법론 개선점: {N}건
```
