---
name: milestone
description: |
  마일스톤 완료 워크플로우를 일괄 실행한다.
  QR 게이트 → delta-log 기록 → 토큰 수집 → 커밋을 순서대로 수행.
trigger-keywords: milestone, 마일스톤, 완료
user-invocable: true
---

## Instructions

마일스톤 완료 시 아래 절차를 순서대로 실행한다.

### Step 1: Tier 확인

```bash
!`cat .claude/agent-forge-state/tier 2>/dev/null || echo "unknown"`
```

Tier가 미설정이면 /complexity를 먼저 실행하도록 안내한다.

### Step 2: QR 게이트 (Micro 제외)

Tier가 micro가 아니면 /qr-gate 절차를 실행한다.

1. 변경된 파일 전수 검사
2. domain-profile 기반 체크리스트 적용
3. MUST/SHOULD/COULD 판정
4. NEEDS_CHANGES이면 수정 후 재검사

PASS 또는 PASS_WITH_CONCERNS가 되면 다음 단계.

### Step 3: delta-log 생성

/delta-log 절차를 실행한다.
delta-logs/ 디렉토리에 M{N}-{slug}.json 생성 + rolling-summary 갱신.

### Step 4: 토큰 수집 (가능한 경우)

token-monitor MCP가 사용 가능하면:
1. `token_session_list`로 현재 세션 확인
2. `token_session_export` (agent-forge 포맷)로 토큰 데이터 추출
3. 프로젝트에 session-log가 있으면 토큰 데이터 기록

사용 불가하면 이 단계를 건너뛰고 안내한다.

### Step 5: 커밋

모든 변경 사항 (코드 + delta-log)을 커밋한다.
커밋 규칙은 프로젝트의 CLAUDE.md를 따른다.
기본: 영어 conventional commits.

### Step 6: 완료 요약

```
## Milestone M{N} Complete
- Tier: {Micro|Standard|Full}
- QR: {결과} (iter {N})
- Delta: delta-logs/M{N}-{slug}.json
- Tokens: {total} (${cost})
- Commit: {hash}
```

### Step 7: Tier 초기화

다음 작업을 위해 tier를 리셋한다:

```bash
!`rm -rf .claude/agent-forge-state`
```
