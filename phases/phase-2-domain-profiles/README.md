# Phase 2: 도메인 프로필 시스템

## 목표

YAML 기반 도메인 프로필로 에이전트 행동을 프로젝트별 커스터마이징.
범용 에이전트가 아닌, 도메인에 특화된 가이드라인을 적용한다.

## 배경

### 범용 에이전트의 한계

같은 "코드 리뷰"라도 도메인에 따라 완전히 다른 기준이 필요하다:

| 도메인 | 최우선 가치 | QR에서 MUST로 취급 | QR에서 COULD로 취급 |
|--------|-----------|-------------------|-------------------|
| 금융 | 규정 준수 | 감사 로그 누락, PII 노출 | 코드 중복 |
| 게임 | 성능 | Hot path에서 GC 유발 | 문서화 부족 |
| 의료 | 안전성 | 입력 검증 누락 | 네이밍 불일치 |
| MVP | 속도 | 크리티컬 버그 | 거의 모든 것 |

범용 에이전트는 이 구분을 하지 못한다.

## 프로필 스키마

```yaml
# domain-profile.yaml

# 메타데이터
domain: fintech
version: "1.0"
description: "금융 서비스 도메인 프로필"

# 우선순위 매트릭스 (0.0 ~ 1.0)
priority_matrix:
  safety: 0.9
  compliance: 0.95
  performance: 0.6
  dev_speed: 0.3
  maintainability: 0.7

# 규약 오버라이드
convention_overrides:
  test_strategy: integration_first    # unit_first | integration_first | property_based
  review_depth: all_severities        # must_only | must_should | all_severities
  documentation_level: regulatory     # minimal | standard | regulatory
  code_style: readability_first       # performance_first | readability_first

# 도메인 지식
domain_knowledge:
  # 도메인 특화 네이밍 규칙
  terminology:
    - term: "transaction"
      meaning: "금융 거래 (반드시 멱등성 보장)"
    - term: "ledger"
      meaning: "원장 (append-only, 삭제 불가)"

  # 절대 하면 안 되는 것
  forbidden_patterns:
    - id: floating_point_currency
      description: "통화 계산에 부동소수점 사용 금지"
      severity: MUST
      alternative: "Decimal 또는 정수(센트 단위) 사용"
    - id: unencrypted_pii
      description: "PII 평문 저장/전송 금지"
      severity: MUST
      alternative: "AES-256 암호화 필수"

  # 반드시 해야 하는 것
  required_patterns:
    - id: audit_trail
      description: "모든 상태 변경에 감사 로그"
      applies_to: "state-changing operations"
    - id: idempotent_transactions
      description: "모든 트랜잭션 멱등성 보장"
      applies_to: "API endpoints, message handlers"

# 워크플로우 커스터마이징
workflow:
  # 복잡도 분기 임계값 조정
  complexity_thresholds:
    micro_max_files: 1          # 금융에서는 단일 파일도 Standard로
    standard_max_files: 5
  # QR 설정
  qr_settings:
    max_iterations: 5
    initial_blocking: all_severities
  # 자동화 수준
  automation_level: conservative    # aggressive | moderate | conservative
```

## 작업 항목

### 2.1 스키마 확정
- [ ] 우선순위 매트릭스 필드 확정
- [ ] 규약 오버라이드 옵션 확정
- [ ] 도메인 지식 구조 확정 (용어, 금지, 필수)
- [ ] 워크플로우 커스터마이징 옵션 확정
- [ ] 스키마 검증 규칙 (필수 필드, 유효 범위)

### 2.2 예시 프로필 3개
- [ ] `profiles/fintech.yaml` — 규정 준수 최우선
- [ ] `profiles/game-dev.yaml` — 성능 최우선
- [ ] `profiles/startup-mvp.yaml` — 속도 최우선

### 2.3 통합 메커니즘 설계
- [ ] 프로필이 컨벤션 계층 Tier 1.5에 삽입되는 방식
- [ ] 에이전트가 프로필을 읽는 시점과 방법
- [ ] 프로필 내 forbidden_patterns가 QR MUST로 변환되는 로직
- [ ] 프로필 내 priority_matrix가 심각도 가중치에 미치는 영향

## 선행 조건

- Phase 1의 컨벤션 계층이 정의되어야 Tier 1.5 삽입 위치 확정

## 완료 기준

- [ ] 3개 이상의 도메인 프로필이 스키마에 맞게 작성
- [ ] 동일 코드에 다른 프로필 적용 시 다른 리뷰 결과가 나오는 것을 시연
- [ ] 프로필 교체가 에이전트 재설정 없이 가능
