---
name: milestone
description: |
  마일스톤 완료 워크플로우를 일괄 실행한다.
  QR 게이트 → delta-log 기록 → handoff 생성 → 토큰 수집 → 커밋을 순서대로 수행.
  Tier별 동적 라우팅: Micro(QR 생략, handoff 생략), Standard(QR 1회), Full(전체 파이프라인).
trigger-keywords: milestone, 마일스톤, 완료
user-invocable: true
---

## Instructions

마일스톤 완료 시 Tier에 따라 적절한 워크플로우를 동적으로 실행한다.

### Step 1: Tier 확인 및 라우팅 결정

```bash
!`cat .agent-forge-state/tier 2>/dev/null || echo "unknown"`
```

Tier가 미설정이면 /complexity를 먼저 실행하도록 안내한다.

**동적 라우팅 테이블:**

| Tier | QR Gate | Delta-Log | Handoff | Token | Commit |
|------|---------|-----------|---------|-------|--------|
| Micro | SKIP | O | SKIP | O | O |
| Standard | 1회 | O | O | O | O |
| Full | 마일스톤별 | O | O (필수) | O | O |

### Step 2: QR 게이트 (Standard/Full만)

> **Micro Tier → 이 단계를 건너뛰고 Step 3으로 이동한다.**

/qr-gate 절차를 실행한다.

1. 변경된 파일 전수 검사
2. domain-profile 기반 체크리스트 적용
3. MUST/SHOULD/COULD 판정
4. NEEDS_CHANGES이면 수정 후 재검사

PASS 또는 PASS_WITH_CONCERNS가 되면 다음 단계.

### Step 3: delta-log 생성

/delta-log 절차를 실행한다.
delta-logs/ 디렉토리에 M{N}-{slug}.json 생성 + rolling-summary 갱신.

### Step 4: handoff.md 생성 (Standard/Full)

> **Micro Tier → 이 단계를 건너뛰고 Step 5로 이동한다.**

세션 인수인계 문서를 생성하여 다음 세션에서 컨텍스트 손실을 방지한다.

`handoff.md` 파일을 프로젝트 루트에 생성 (기존 파일이 있으면 덮어쓴다):

```markdown
# Handoff — M{N} {slug}

> Generated at: {ISO 8601 UTC}
> Tier: {Micro|Standard|Full}

## Current State

{현재 프로젝트의 동작 상태를 1-2문장으로 요약}

## What Was Done (This Session)

{이번 세션에서 완료한 작업 목록}
- {변경 파일 1}: {변경 내용}
- {변경 파일 2}: {변경 내용}

## Key Decisions

{결정 사항과 그 근거를 간략히}
- {결정 1}: {근거}

## Unresolved / Known Issues

{미해결 사항이나 알려진 이슈}
- [ ] {이슈 1}

## Next Steps

{다음 세션에서 해야 할 작업}
1. {다음 단계 1}
2. {다음 단계 2}

## Environment Notes

{다음 세션에서 알아야 할 환경 정보 (브랜치, 의존성 변경 등)}
- Branch: {current branch}
- Dependencies changed: {yes/no}
```

handoff.md의 내용은 해당 세션의 delta-log(M{N}-{slug}.json)와 rolling-summary.md를 기반으로 작성한다. 중복을 피하되, delta-log보다 **행동 지향적**으로 작성한다 (다음 사람이 즉시 시작할 수 있도록).

**Full Tier 추가 규칙**: Full Tier에서는 handoff.md에 마일스톤 진행 현황 섹션을 추가한다:

```markdown
## Milestone Progress

| Milestone | Status | Key Output |
|-----------|--------|------------|
| M{N-2} | Done | {output} |
| M{N-1} | Done | {output} |
| M{N} | Done (current) | {output} |
| M{N+1} | Planned | {description} |
```

### Step 5: 토큰 수집 (가능한 경우)

token-monitor MCP가 사용 가능하면:
1. `token_session_list`로 현재 세션 확인
2. `token_session_export` (agent-forge 포맷)로 토큰 데이터 추출
3. 프로젝트에 session-log가 있으면 토큰 데이터 기록

사용 불가하면 이 단계를 건너뛰고 안내한다.

### Step 6: 커밋

모든 변경 사항 (코드 + delta-log + handoff.md)을 커밋한다.
커밋 규칙은 프로젝트의 CLAUDE.md를 따른다.
기본: 영어 conventional commits.

### Step 7: 완료 요약

Tier별 요약 형식:

**Micro:**
```
## Milestone M{N} Complete (Micro — Fast Path)
- Delta: delta-logs/M{N}-{slug}.json
- Tokens: {total} (${cost})
- Commit: {hash}
```

**Standard:**
```
## Milestone M{N} Complete (Standard)
- QR: {결과} (iter {N})
- Delta: delta-logs/M{N}-{slug}.json
- Handoff: handoff.md
- Tokens: {total} (${cost})
- Commit: {hash}
```

**Full:**
```
## Milestone M{N} Complete (Full)
- QR: {결과} (iter {N})
- Delta: delta-logs/M{N}-{slug}.json
- Handoff: handoff.md (with milestone progress)
- Tokens: {total} (${cost})
- Commit: {hash}
- Progress: M{N} of {total milestones}
```

### Step 8: Tier 초기화

다음 작업을 위해 tier를 리셋한다:

```bash
!`rm -rf .agent-forge-state`
```
