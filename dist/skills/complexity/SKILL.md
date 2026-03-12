---
name: complexity
description: |
  작업의 복잡도를 평가하고 워크플로우 Tier(Micro/Standard/Full)를 추천한다.
  작업 시작 시 호출하여 적절한 검증 수준을 결정한다.
trigger-keywords: complexity, 복잡도, tier, 티어
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

```bash
!`mkdir -p .claude/agent-forge-state && echo "{tier}" > .claude/agent-forge-state/tier && echo "Tier set: {tier}"`
```

### Step 4: 출력

```
## Complexity Assessment
- 예상 파일 수: {N}개
- 의존성 영향: {없음|로컬|넓음}
- 아키텍처 영향: {없음|경미|중대}
- **Tier: {Micro|Standard|Full}**
- 워크플로우: {절차 요약}
```

사용자가 수동 오버라이드를 요청하면 해당 Tier를 적용한다.
단, 다운그레이드(Full→Standard, Standard→Micro)는 허용하지 않는다.
