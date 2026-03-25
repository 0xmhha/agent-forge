---
name: complexity
description: |
  작업의 복잡도를 평가하고 워크플로우 Tier(Micro/Standard/Full)를 추천한다.
  작업 시작 시 호출하여 적절한 검증 수준을 결정한다.
  Full Tier 판정 시 마일스톤 자동 분해 계획을 제안한다.
trigger-keywords: complexity, 복잡도, tier, 티어, 작업 시작
user-invocable: true
---

## Instructions

현재 작업의 복잡도를 평가하여 Tier를 결정한다.

### Step 1: 변경 범위 파악

사용자가 요청한 작업을 분석한다:
- 예상 변경 파일 수
- 의존성 영향 범위 (로컬 / 패키지 내 / 다중 패키지)
- 아키텍처 영향 (없음 / 경미 / 중대)

### Step 2: Tier 판정

```
IF 파일 수 <= 2 AND 의존성 영향 없음:
  → Micro (QR 생략, 계획 생략)

ELSE IF 파일 수 <= 10 AND 아키텍처 영향 경미:
  → Standard (간략 계획, QR 1회)

ELSE:
  → Full (상세 계획, 마일스톤별 QR)
```

도메인 프로필(`domain-profile.yaml`)이 프로젝트에 있으면 `complexity_thresholds`로 기준을 조정한다.

### Step 3: Tier 기록

tier 값은 반드시 소문자로 기록한다: `micro`, `standard`, `full`

```bash
!`mkdir -p .agent-forge-state && echo "{tier}" > .agent-forge-state/tier && echo "Tier set: {tier}"`
```

> **중요**: `.agent-forge-state/tier` 에 기록하는 값은 반드시 소문자여야 한다.
> hooks가 `micro`, `standard`, `full` 소문자로 비교하기 때문이다.

### Step 4: Tier별 출력

#### Micro / Standard 출력:

```
## Complexity Assessment
- 예상 파일 수: {N}개
- 의존성 영향: {없음|로컬|넓음}
- 아키텍처 영향: {없음|경미|중대}
- **Tier: {Micro|Standard}**
- 워크플로우: {절차 요약}
```

#### Full Tier 출력 (자동 마일스톤 분해 포함):

Full Tier로 판정되면 자동으로 마일스톤 분해 계획을 생성한다.

```
## Complexity Assessment
- 예상 파일 수: {N}개
- 의존성 영향: {넓음}
- 아키텍처 영향: {경미|중대}
- **Tier: Full**
- 워크플로우: 상세 계획 → 마일스톤별 (실행 → QR) → 커밋
```

**마일스톤 분해 절차:**

1. 작업을 독립적인 마일스톤으로 분해한다:
   - 각 마일스톤은 단독으로 커밋 가능한 단위
   - 마일스톤 간 의존성을 최소화
   - 각 마일스톤에 예상 파일 수와 핵심 산출물을 명시

2. 분해 결과를 테이블로 출력:

```
### Milestone Plan

| # | Milestone | 예상 파일 수 | 핵심 산출물 | 의존성 |
|---|-----------|-------------|-----------|--------|
| M{N+1} | {제목} | {N}개 | {산출물} | — |
| M{N+2} | {제목} | {N}개 | {산출물} | M{N+1} |
| M{N+3} | {제목} | {N}개 | {산출물} | M{N+1} |
| M{N+4} | {제목} | {N}개 | {산출물} | M{N+2}, M{N+3} |

### Execution Order

의존성 없는 마일스톤은 병렬 실행 가능:
- Wave 1: M{N+1} (기반)
- Wave 2: M{N+2}, M{N+3} (병렬 가능)
- Wave 3: M{N+4} (통합)

### Per-Milestone Workflow
각 마일스톤은 독립적으로 다음 절차를 수행:
  코딩 → /qr-gate → /delta-log → /handoff(마지막 마일스톤) → 커밋
```

3. 마일스톤 분해 기준:
   - **기능 경계**: 독립적인 기능 단위로 분리
   - **테스트 가능성**: 각 마일스톤이 독립적으로 테스트 가능
   - **롤백 용이성**: 각 마일스톤을 개별 revert 가능
   - **균등 분배**: 마일스톤 간 작업량 균등 (±30% 이내)

4. 마일스톤 수 기록:

```bash
!`echo "{total_milestones}" > .agent-forge-state/total-milestones`
```

### Step 5: 사용자 확인

Full Tier의 마일스톤 계획은 반드시 사용자 확인을 받는다.

```
위 마일스톤 계획을 확인해주세요.
- 승인: 첫 번째 마일스톤부터 시작합니다.
- 수정: 변경할 부분을 알려주세요.
```

사용자가 수동 오버라이드를 요청하면 해당 Tier를 적용한다.
단, 다운그레이드(Full→Standard, Standard→Micro)는 허용하지 않는다.
