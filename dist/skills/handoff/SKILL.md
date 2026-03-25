---
name: handoff
description: |
  세션 종료 시 다음 세션을 위한 인수인계 문서(handoff.md)를 생성한다.
  현재 상태, 완료 작업, 미해결 사항, 다음 단계를 구조화하여 기록한다.
  /milestone 워크플로우에 포함되지만, 독립적으로도 호출 가능.
trigger-keywords: handoff, 인수인계, 핸드오프, session end, 세션 종료
user-invocable: true
---

## Instructions

세션 종료 시 또는 작업 전환 시 다음 세션을 위한 인수인계 문서를 생성한다.

### Step 1: 현재 상태 수집

1. 프로젝트 상태 확인:
```bash
!`git status --short`
```

2. 현재 브랜치:
```bash
!`git branch --show-current`
```

3. 최근 커밋:
```bash
!`git log --oneline -5`
```

4. delta-logs에서 최신 마일스톤 확인:
```bash
!`ls delta-logs/M*.json 2>/dev/null | sort -V | tail -1 || echo "no delta-logs"`
```

5. rolling-summary가 있으면 읽기:
```bash
!`cat delta-logs/rolling-summary.md 2>/dev/null | head -50 || echo "no rolling-summary"`
```

### Step 2: 세션 작업 내역 정리

이번 세션에서 수행한 작업을 정리한다:
- 변경된 파일 목록과 각 파일의 변경 내용
- 내린 결정과 그 근거
- 발생한 이슈와 해결 방법

### Step 3: handoff.md 생성

프로젝트 루트에 `handoff.md`를 생성한다 (기존 파일이 있으면 덮어쓴다):

```markdown
# Handoff — {작업 제목 또는 마일스톤}

> Generated at: {ISO 8601 UTC}
> Branch: {current branch}

## Current State

{현재 프로젝트의 동작 상태를 1-2문장으로 요약}
{빌드 가능 여부, 테스트 통과 여부 등}

## What Was Done (This Session)

{이번 세션에서 완료한 작업 목록}
- `{파일 경로}`: {변경 내용}
- `{파일 경로}`: {변경 내용}

## Key Decisions

{결정 사항과 그 근거}
- **{결정 1}**: {근거}
- **{결정 2}**: {근거}

## Unresolved / Known Issues

{미해결 사항이나 알려진 이슈}
- [ ] {이슈 1}: {상세}
- [ ] {이슈 2}: {상세}

## Next Steps

{다음 세션에서 해야 할 작업, 우선순위 순}
1. {다음 단계 1}
2. {다음 단계 2}
3. {다음 단계 3}

## Environment Notes

{다음 세션에서 알아야 할 환경 정보}
- Branch: {current branch}
- Uncommitted changes: {yes/no — 있으면 상세}
- Dependencies changed: {yes/no — 있으면 어떤 패키지}
- Config changes: {있으면 상세}
```

### Step 4: 작성 원칙

handoff.md 작성 시 다음 원칙을 따른다:

1. **행동 지향적**: "무엇을 했다"가 아니라 "다음에 무엇을 해야 한다"에 초점
2. **구체적**: 파일 경로, 함수명, 라인 번호 등 구체적 참조 포함
3. **독립적**: delta-log이나 rolling-summary를 읽지 않아도 이해 가능해야 함
4. **Temporal 규칙 준수**: "방금", "아까", "이전에" 같은 시간 참조 대신 절대적 설명 사용
5. **간결함**: 핵심 정보만 포함, 불필요한 배경 설명 생략

### Step 5: 완료 보고

```
## Handoff Complete

- File: handoff.md
- Branch: {branch}
- Uncommitted: {yes/no}
- Next priority: {가장 중요한 다음 단계}

다음 세션 시작 시 `handoff.md`를 읽어주세요.
```
