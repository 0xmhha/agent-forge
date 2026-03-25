---
name: qr-gate
description: |
  Quality Review 게이트를 실행한다. 커밋 전에 코드 품질을 검증하는 핵심 단계.
  Standard/Full tier에서 필수. Micro에서는 선택.
  MUST/SHOULD/COULD 3단계 심각도, domain-profile 연동, 이중 경로 검증.
  NEEDS_CHANGES 시 자동 수정 루프(최대 2회) 후 수동 전환.
trigger-keywords: qr, quality review, 품질 검증, 코드 검토
user-invocable: true
---

## Instructions

### Step 1: 컨텍스트 수집

1. 프로젝트의 CLAUDE.md 읽기 (있으면)
2. 프로젝트의 domain-profile.yaml 읽기 (있으면)
3. 변경 범위 파악:

```bash
!`git diff --stat`
```

4. 현재 반복 횟수 확인:

```bash
!`cat .agent-forge-state/qr-iteration 2>/dev/null || echo "1"`
```

### Step 2: 도메인 프로필 체크리스트 생성

domain-profile.yaml이 프로젝트에 있으면:
- `forbidden_patterns` → 위반 여부 검사 항목으로 변환
- `required_patterns` → 존재 여부 검사 항목으로 변환
- `priority_matrix` → 심각도 가중치 조정:
  - 0.9~1.0 → SHOULD를 MUST로 승격 가능
  - 0.3~0.5 → SHOULD를 COULD로 강등 가능
  - 0.0~0.2 → 관련 검사 생략 가능

`applies_to` 필드가 있으면 해당 모듈에만 적용한다.

### Step 3: 사실 수집

변경된 파일을 모두 읽고, 코드에서 관찰 가능한 사실만 수집한다.
의도 추측 금지.

### Step 4: 규칙 적용

- **MUST**: "프로덕션에 복구 불가능한 결과를 초래하는가?" → MUST
  - SECURITY_VIOLATION, DATA_LOSS_RISK, CONTRACT_VIOLATION
- **SHOULD**: "6개월 후 유지보수를 어렵게 하는가?" → SHOULD
  - GOD_OBJECT, DUPLICATE_LOGIC, TESTING_GAP
- **COULD**: "린터/포매터로 자동 수정 가능한가?" → COULD
  - DEAD_CODE, FORMATTER_FIXABLE

**반복별 디에스컬레이션 (iteration-based de-escalation):**

| 반복 | 차단 수준 | 설명 |
|------|-----------|------|
| 1-2회 | MUST + SHOULD + COULD | 모든 심각도 보고 |
| 3-4회 | MUST + SHOULD | COULD 자동 무시 |
| 5+회 | MUST only | MUST만 차단 |

### Step 5: 이중 경로 검증 (MUST에만)

- 경로 A: "이것이 문제인 이유는?"
- 경로 B: "이것이 문제가 아닌 이유는?"
- B가 더 설득력 있으면 → SHOULD로 하향

### Step 6: 출력

```
VERDICT: [PASS | PASS_WITH_CONCERNS | NEEDS_CHANGES]
ITERATION: {N}/2 (auto-fix) 또는 {N} (manual)

FINDINGS:
### [CATEGORY SEVERITY]: Title
- Location: file:line
- Issue: description
- Impact: consequence
- Fix: action

REASONING: [max 30 words]
```

### Step 7: 자동 수정 루프 (NEEDS_CHANGES인 경우)

NEEDS_CHANGES 판정이 나오면 자동 수정 루프를 실행한다.

**자동 수정 조건:**
- 현재 반복 횟수 ≤ 2
- MUST 또는 SHOULD finding이 존재

**자동 수정 절차:**

1. FINDINGS를 구조화된 수정 지시로 변환:
   ```
   각 finding에 대해:
   - 파일: {file}:{line}
   - 문제: {issue}
   - 수정 방법: {fix action}
   ```

2. 수정 실행:
   - 각 finding의 Fix 항목에 따라 코드를 직접 수정
   - COULD 항목은 자동 수정 시 무시 (린터/포매터 영역)
   - 수정 시 기존 코드 스타일과 패턴을 유지

3. 반복 횟수 기록:
   ```bash
   !`mkdir -p .agent-forge-state && echo "{N+1}" > .agent-forge-state/qr-iteration`
   ```

4. Step 1로 돌아가 재검사 실행

**수동 전환 조건 (반복 횟수 > 2):**

```
## QR Auto-Fix Limit Reached

자동 수정을 2회 시도했으나 여전히 NEEDS_CHANGES입니다.

### 남은 Finding:
{미해결 findings 목록}

### 수정 이력:
- Iteration 1: {수정한 항목}
- Iteration 2: {수정한 항목}

수동으로 남은 이슈를 수정한 후 `/qr-gate`를 다시 실행해주세요.
```

### Step 8: QR 완료 기록

PASS 또는 PASS_WITH_CONCERNS인 경우:

```bash
!`mkdir -p .agent-forge-state && echo "yes" > .agent-forge-state/qr-done && echo "QR gate completed"`
```

반복 카운터 리셋:
```bash
!`rm -f .agent-forge-state/qr-iteration`
```
