---
name: complexity
description: |
  작업의 복잡도를 평가하고 워크플로우 Tier(Micro/Standard/Full)를 추천한다.
  작업 시작 시 자동 호출되거나 /complexity로 수동 호출.
trigger-keywords: complexity, 복잡도, tier, 티어
user-invocable: true
---

## Instructions

현재 작업의 복잡도를 평가하여 Tier를 결정한다.

### Step 1: 변경 범위 파악

예상 변경 파일 수, 의존성 영향, 아키텍처 영향을 분석한다.

### Step 2: Tier 판정

```
IF 파일 수 <= 2 AND 의존성 영향 없음:
  → Micro (QR 생략, 계획 생략)

ELSE IF 파일 수 <= 10 AND 아키텍처 영향 경미:
  → Standard (간략 계획, QR 1회)

ELSE:
  → Full (상세 계획, 마일스톤별 QR)
```

도메인 프로필에 `complexity_thresholds`가 있으면 해당 값으로 오버라이드한다.
domain-profile.yaml을 확인:

```bash
!`cat tools/workspace-mcp/domain-profile.yaml 2>/dev/null | grep -A3 complexity_thresholds || echo "no domain profile thresholds"`
```

### Step 3: Tier 기록

결정된 Tier를 임시 파일에 기록하여 hooks가 참조할 수 있게 한다:

```bash
!`echo "{tier}" > /tmp/agent-forge-tier && echo "Tier set: {tier}"`
```

### Step 4: 출력

```
## Complexity Assessment
- 예상 파일 수: {N}개
- 의존성 영향: {없음|로컬|넓음}
- 아키텍처 영향: {없음|경미|중대}
- **판정: {Micro|Standard|Full}**
- 워크플로우: {해당 tier의 절차 요약}
```

사용자가 수동 오버라이드를 요청하면 해당 Tier를 적용한다.
단, 다운그레이드(Full→Standard, Standard→Micro)는 허용하지 않는다.
