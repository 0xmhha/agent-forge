# 도메인 프로필 통합 가이드

## 개요

도메인 프로필은 에이전트의 행동을 프로젝트 도메인에 맞게 커스터마이징하는 YAML 설정이다.
이 문서는 프로필이 기존 컨벤션 시스템과 어떻게 통합되는지 설명한다.

---

## 1. 4-Tier 계층에서의 위치: Tier 1.5

도메인 프로필은 **Tier 1.5**로, Tier 1(사용자 명시 지시)과 Tier 2(프로젝트 문서) 사이에 위치한다.

```
Tier 1: User Explicit     ← 사용자가 세션에서 직접 지시 (절대 우선)
Tier 1.5: Domain Profile   ← domain-profile.yaml (이 문서의 주제)
Tier 2: Project Docs       ← CLAUDE.md, README.md 등
Tier 3: Structural Defaults ← 기본 규약 (God Object 임계값 등)
```

**왜 Tier 1.5인가?**

- Tier 2(프로젝트 문서)보다 상위: 도메인 프로필은 프로젝트의 근본적 제약을 정의한다.
  README에 "테스트 커버리지 80%" 라고 써있어도, 금융 도메인 프로필이
  `test_strategy: integration_first`를 지정하면 통합 테스트가 우선된다.
- Tier 1(사용자 지시)보다 하위: 사용자가 "이번에는 성능 우선"이라고 하면,
  프로필의 `code_style: readability_first`는 무시된다.

---

## 2. forbidden_patterns → QR MUST 변환

도메인 프로필의 `forbidden_patterns`는 QR(Quality Review) 시스템의 발견 사항으로 자동 변환된다.

### 변환 규칙

| forbidden_patterns.severity | QR 심각도 | 차단 여부 |
|----------------------------|----------|----------|
| MUST | MUST | 모든 반복에서 차단 |
| SHOULD | SHOULD | iter 1-4에서 차단, iter 5+에서 해제 |
| COULD | COULD | iter 1-2에서만 차단 |

### 변환 예시

프로필 정의:
```yaml
forbidden_patterns:
  - id: floating_point_currency
    description: "통화 계산에 부동소수점 사용 금지"
    severity: MUST
    alternative: "Decimal 또는 정수(센트 단위) 사용"
```

QR 출력:
```
### [FLOATING_POINT_CURRENCY MUST]: 통화 계산에 float 사용 감지
- Location: src/payment/calculator.ts:42
- Source: Tier 1.5 (domain profile: fintech, forbidden_pattern)
- Issue: price 변수가 number(float64) 타입으로 통화 계산에 사용됨
- Impact: IEEE 754 부동소수점 정밀도 손실로 금액 오차 발생 가능
- Fix: Decimal 라이브러리 또는 정수(센트 단위) 사용
```

### detection_method 활용

`detection_method` 필드는 에이전트가 코드에서 패턴을 **어떻게 검사하는지** 구체적으로 기술한다.
단순 힌트가 아니라, 검사 대상 범위와 절차를 포함해야 한다.

```yaml
detection_method: "grep으로 return.*ToolResult 지점을 전수 검사. 각 반환 값의 error 필드에 토큰 패턴(ghp_, gho_, sk-) 포함 여부 확인"
```

**좋은 detection_method 작성 가이드**:
- **범위**: 어떤 파일/함수를 검사하는가 (예: "모든 API 핸들러", "return 문")
- **방법**: grep, AST 검사, 변수 추적 등 구체적 도구/기법
- **판정**: 어떤 상태이면 위반으로 판정하는가

에이전트는 이 방법을 기반으로 검사하되, 추가적인 도메인 지식 기반 탐지도 수행할 수 있다.

---

## 3. priority_matrix → 심각도 가중치 조정

`priority_matrix`는 QR 발견 사항의 실질적 심각도를 도메인 맥락에 맞게 조정한다.

### 조정 메커니즘

기본 QR 규칙(Tier 3)의 심각도를 도메인 우선순위에 따라 승격/강등한다:

```
조정된 심각도 = 기본 심각도 × (관련 priority_matrix 값)
```

### 구체적 예시

**GOD_FUNCTION (기본: SHOULD)** 규칙이 각 도메인에서 어떻게 달라지는가:

| 도메인 | maintainability 값 | 조정 결과 | 이유 |
|--------|-------------------|----------|------|
| fintech | 0.7 | SHOULD 유지 | 유지보수성이 중요하므로 기본 심각도 유지 |
| game-dev | 0.5 | COULD로 강등 | 성능을 위해 긴 함수 허용, 유지보수성 양보 |
| startup-mvp | 0.3 | 검사 생략 | 유지보수성 우선순위가 극히 낮아 검사 불필요 |

**TESTING_GAP (기본: SHOULD)** 규칙:

| 도메인 | 관련 값 | 조정 결과 | 이유 |
|--------|--------|----------|------|
| fintech | compliance: 0.95 | MUST로 승격 | 규제 환경에서 테스트 누락은 치명적 |
| game-dev | performance: 0.95 | SHOULD 유지 | Hot path 테스트는 중요 |
| startup-mvp | dev_speed: 0.95 | COULD로 강등 | 핵심 플로우만 E2E로 검증 |

### 승격/강등 임계값

| priority_matrix 값 | 효과 |
|-------------------|------|
| 0.9~1.0 | 관련 SHOULD를 MUST로 승격 가능 |
| 0.6~0.8 | 기본 심각도 유지 |
| 0.3~0.5 | 관련 SHOULD를 COULD로 강등 가능 |
| 0.0~0.2 | 관련 검사 생략 가능 |

---

## 4. convention_overrides → 에이전트 행동 변경

`convention_overrides`는 에이전트의 기본 동작을 도메인에 맞게 재정의한다.

### test_strategy

에이전트가 테스트를 제안하거나 생성할 때의 우선순위를 결정한다.

| 값 | 에이전트 행동 |
|----|-------------|
| `unit_first` | 순수 함수 단위 테스트 우선 제안, 모킹 적극 활용 |
| `integration_first` | 시스템 간 통합 테스트 우선, 실제 의존성과 함께 테스트 |
| `e2e_first` | 사용자 시나리오 기반 E2E 테스트, 핵심 플로우만 검증 |
| `property_based` | 속성 기반 테스트로 불변성 검증, 경계값 자동 탐색 |

### review_depth

QR이 어느 심각도까지 발견 사항을 보고하고 차단하는지 결정한다.

| 값 | 보고 범위 | 차단 범위 |
|----|----------|----------|
| `must_only` | MUST만 보고 | MUST만 차단 |
| `must_should` | MUST + SHOULD 보고 | 둘 다 차단 |
| `all_severities` | 전체 보고 | Iteration Escalation 규칙 적용 |

### documentation_level

에이전트가 문서화 누락을 얼마나 엄격하게 지적하는지 결정한다.

| 값 | 요구 수준 |
|----|----------|
| `minimal` | 핵심 API 사용법만 (README + 환경 설정) |
| `standard` | 공개 인터페이스 + 주요 아키텍처 결정 기록 |
| `comprehensive` | 모든 공개 함수 + 내부 설계 근거 |
| `regulatory` | 규제 감사 대응 수준 (변경 이력, 승인 기록 포함) |

### code_style

가독성과 성능이 충돌할 때 에이전트의 판단 기준을 결정한다.

| 값 | 에이전트 판단 |
|----|-------------|
| `readability_first` | 명확한 변수명, 단순한 구조 우선. 최적화 제안 자제. |
| `performance_first` | 인라인, 캐시 친화 구조, 비트 연산 등 허용. 가독성 트레이드오프 수용. |
| `balanced` | 상황에 따라 판단. Hot path에서만 성능 우선. |

---

## 5. 프로필 전환 메커니즘

### 단일 도메인 프로젝트

프로젝트 루트에 `domain-profile.yaml` 배치:

```
project-root/
  domain-profile.yaml    ← 에이전트가 자동 감지
  src/
  tests/
```

### 멀티 도메인 프로젝트

디렉토리별 프로필 적용:

```
project-root/
  domain-profile.yaml         ← 기본 프로필 (예: startup-mvp)
  services/
    payment/
      domain-profile.yaml     ← 결제 모듈은 fintech 프로필
    game-engine/
      domain-profile.yaml     ← 게임 엔진은 game-dev 프로필
```

**적용 규칙**:
1. 현재 작업 파일에서 가장 가까운 상위 디렉토리의 `domain-profile.yaml` 적용
2. 디렉토리별 프로필이 없으면 프로젝트 루트 프로필 적용
3. 루트 프로필도 없으면 프로필 미적용 (Tier 3 기본값만 사용)

### 프로필 전환 시점

에이전트는 다음 시점에 프로필을 (재)로딩한다:

1. **세션 시작 시**: 프로젝트 루트의 `domain-profile.yaml` 자동 로딩
2. **파일 전환 시**: 다른 디렉토리의 파일 작업 시 해당 디렉토리의 프로필 확인
3. **사용자 명시 지시**: "이 코드는 fintech 기준으로 리뷰해줘"

프로필 전환은 에이전트 재시작 없이 즉시 적용된다.

---

## 6. 적용 예시: 동일 코드, 다른 프로필

다음 코드를 fintech와 startup-mvp 프로필로 각각 리뷰한 결과를 비교한다.

### 대상 코드

```typescript
async function processPayment(userId: string, amount: number) {
  const user = await db.query(`SELECT * FROM users WHERE id = '${userId}'`);
  const result = await paymentGateway.charge(user.email, amount);
  if (result.success) {
    await db.query(`UPDATE balances SET amount = ${amount} WHERE user_id = '${userId}'`);
  }
  return result;
}
```

### Fintech 프로필 적용 결과

```
VERDICT: NEEDS_CHANGES

FINDINGS:
### [FLOATING_POINT_CURRENCY MUST]: 통화 금액에 number(float) 사용
- Location: payment.ts:1
- Source: Tier 1.5 (fintech: floating_point_currency)
- Issue: amount 파라미터가 number 타입으로 부동소수점 연산됨
- Impact: 금액 계산 시 정밀도 손실 (예: 0.1 + 0.2 !== 0.3)
- Fix: Decimal 라이브러리 또는 정수(센트 단위) 사용

### [UNPARAMETERIZED_QUERIES MUST]: SQL 인젝션 취약점
- Location: payment.ts:2,4
- Source: Tier 1.5 (fintech: unparameterized_queries)
- Issue: 문자열 보간으로 SQL 쿼리 구성, 파라미터 바인딩 미사용
- Impact: SQL 인젝션으로 금융 데이터 유출/변조 가능
- Fix: Prepared Statement 사용

### [DIRECT_DB_MUTATION_WITHOUT_AUDIT MUST]: 감사 로그 없는 잔액 변경
- Location: payment.ts:4
- Source: Tier 1.5 (fintech: direct_db_mutation_without_audit)
- Issue: balances 테이블 UPDATE에 감사 로그 기록 없음
- Impact: SOX 규정 위반, 변경 추적 불가
- Fix: audit_log 테이블에 변경 전/후 값 기록

### [SILENT_TRANSACTION_FAILURE MUST]: 결제 실패 시 에러 처리 부재
- Location: payment.ts:3-5
- Source: Tier 1.5 (fintech: silent_transaction_failure)
- Issue: paymentGateway.charge 실패 시 에러 로깅/알림 없음
- Impact: 자금 불일치 발생 가능
- Fix: try-catch + 명시적 에러 로깅 + 알림 발송

### [AUDIT_TRAIL MUST]: 감사 추적 패턴 누락
- Location: payment.ts (전체 함수)
- Source: Tier 1.5 (fintech: required_pattern audit_trail)
- Issue: 상태 변경 함수에 who/what/when/before/after 로깅 없음
- Fix: 감사 로그 미들웨어 또는 명시적 로깅 추가

### [IDEMPOTENT_TRANSACTIONS MUST]: 멱등성 보장 메커니즘 부재
- Location: payment.ts:1
- Source: Tier 1.5 (fintech: required_pattern idempotent_transactions)
- Issue: idempotency key 파라미터 없음, 재시도 시 이중 결제 가능
- Fix: idempotency key 기반 중복 요청 감지 로직 추가

REASONING: 금융 도메인에서 6개 MUST 위반. 보안, 감사, 데이터 정합성 모두 미달.
```

### Startup MVP 프로필 적용 결과

```
VERDICT: PASS_WITH_CONCERNS

FINDINGS:
### [COMPLEX_AUTH_FROM_SCRATCH MUST]: SQL 인젝션 취약점
- Location: payment.ts:2,4
- Source: Tier 1 (QR 기본 규칙: SECURITY_VIOLATION)
- Issue: 문자열 보간으로 SQL 쿼리 구성
- Impact: 사용자 데이터 유출 위험
- Fix: ORM 또는 Prepared Statement 사용

REASONING: 보안 취약점 1건 수정 필요. 나머지는 MVP 단계에서 수용 가능한 기술 부채.
```

### 비교 요약

| 항목 | Fintech | Startup MVP |
|------|---------|-------------|
| 총 발견 수 | 6 MUST | 1 MUST |
| 판정 | NEEDS_CHANGES | PASS_WITH_CONCERNS |
| float 통화 | MUST 차단 | 무시 (성능 아님, 정밀도도 MVP에서 충분) |
| 감사 로그 | MUST 차단 | 무시 (규제 대상 아님) |
| 멱등성 | MUST 차단 | 무시 (트래픽 낮아 이중 결제 확률 극소) |
| SQL 인젝션 | MUST 차단 | MUST 차단 (보안은 도메인 무관 기본 규칙) |

이 차이가 도메인 프로필의 핵심 가치다.
**동일한 코드가 도메인 맥락에 따라 완전히 다른 리뷰 결과를 받는다.**

---

## 7. 프로필 로딩 순서

에이전트가 작업을 시작할 때의 설정 로딩 순서:

```
1. Tier 3 기본값 로딩 (structural defaults)
2. domain-profile.yaml 로딩 (Tier 1.5)
   a. priority_matrix → 심각도 가중치 테이블 조정
   b. convention_overrides → 기본 규약 재정의
   c. domain_knowledge → 용어집, 금지/필수 패턴 등록
   d. workflow → 프로세스 모델 파라미터 조정
3. 프로젝트 문서 로딩 (Tier 2: CLAUDE.md, README.md)
4. 사용자 지시 수신 대기 (Tier 1)
```

각 단계에서 상위 tier가 하위 tier의 값을 오버라이드한다.
같은 설정에 대해 여러 tier에서 값이 정의된 경우, 가장 높은 tier의 값이 적용된다.
