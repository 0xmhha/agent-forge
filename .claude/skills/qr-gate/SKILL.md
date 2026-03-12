---
name: qr-gate
description: |
  Quality Review 게이트를 실행한다. 커밋 전에 코드 품질을 검증하는 핵심 단계.
  Standard/Full tier에서 필수. /qr-gate로 수동 호출 또는 /milestone에서 자동 호출.
trigger-keywords: qr, quality review, 리뷰, 검토
user-invocable: true
---

## Instructions

### Step 1: 컨텍스트 수집

- CLAUDE.md 읽기
- 해당 도구의 domain-profile.yaml 읽기 (있는 경우)
- `git diff --stat`으로 변경 범위 파악

### Step 2: 도메인 프로필 체크리스트 생성

도메인 프로필이 있으면:
- `forbidden_patterns` → 위반 여부 검사 항목으로 변환
- `required_patterns` → 존재 여부 검사 항목으로 변환
- `priority_matrix` → 심각도 가중치 조정:
  - 0.9~1.0 → SHOULD를 MUST로 승격 가능
  - 0.3~0.5 → SHOULD를 COULD로 강등 가능
  - 0.0~0.2 → 관련 검사 생략 가능

`applies_to` 필드가 있으면 현재 작업 대상에 해당하는 패턴만 검사한다.

### Step 3: 사실 수집

변경된 파일을 모두 읽고, 코드에서 관찰 가능한 사실만 수집한다.
의도 추측 금지.

### Step 4: 규칙 적용

- **MUST 판정**: "이것이 프로덕션에서 어떤 결과를 초래하는가?" → 복구 불가능하면 MUST
- **SHOULD 판정**: "6개월 후 유지보수를 어렵게 하는가?" → 그렇다면 SHOULD
- **COULD 판정**: "린터/포매터로 자동 수정 가능한가?" → 가능하면 COULD

### Step 5: 이중 경로 검증 (MUST에만)

- 경로 A: "이것이 문제인 이유는?"
- 경로 B: "이것이 문제가 아닌 이유는?"
- B가 더 설득력 있으면 → SHOULD로 하향

### Step 6: 출력

```
VERDICT: [PASS | PASS_WITH_CONCERNS | NEEDS_CHANGES]

FINDINGS:
### [CATEGORY SEVERITY]: Title
- Location: file:line
- Issue: description
- Impact: consequence
- Fix: action

REASONING: [max 30 words]
```

### Step 7: QR 완료 기록

```bash
!`echo "yes" > /tmp/agent-forge-qr-done && echo "QR gate completed"`
```

NEEDS_CHANGES이면 발견된 문제를 수정한 후 다시 /qr-gate를 실행한다.
