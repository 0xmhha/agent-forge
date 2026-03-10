# Convention Tiers

## 4-Tier Priority System

규칙 간 충돌이 발생할 때, 상위 tier가 항상 승리한다.
같은 tier 내에서는 더 구체적인 규칙이 승리한다.

---

## Tier 정의

### Tier 1: User Explicit (사용자 명시 지시)

사용자가 현재 세션에서 직접 지시한 것. 절대 우선.

**예시**:
- "이 프로젝트에서는 snake_case를 사용해"
- "테스트는 작성하지 마"
- "성능보다 가독성을 우선해"

**특성**:
- 세션 범위 (해당 세션에서만 유효)
- 명시적이어야 함 (추론하지 않음)
- 다른 모든 tier를 오버라이드

### Tier 1.5: Domain Profile (도메인 프로필)

프로젝트의 도메인 프로필 (`domain-profile.yaml`)에 정의된 규칙.

**예시**:
- `forbidden_patterns: floating_point_currency` (금융)
- `required_patterns: audit_trail` (금융)
- `convention_overrides: test_strategy: integration_first` (금융)

**특성**:
- 프로젝트 범위 (해당 프로젝트에서 항상 유효)
- 도메인 지식 반영
- Tier 1에 의해서만 오버라이드
- Phase 2에서 구현

### Tier 2: Project Documentation (프로젝트 문서)

프로젝트의 CLAUDE.md, README.md, CONTRIBUTING.md 등에 문서화된 규칙.

**예시**:
- CLAUDE.md: "이 프로젝트는 TypeScript strict mode를 사용"
- README.md: "모든 API 응답은 envelope 패턴을 따름"
- CONTRIBUTING.md: "PR은 squash merge만 허용"

**특성**:
- 프로젝트 범위
- 코드에서 발견할 수 있는 것은 여기에 두지 않음 (보이지 않는 지식만)
- Tier 1, 1.5에 의해 오버라이드

### Tier 3: Structural Defaults (기본 규약)

프로젝트 문서가 침묵할 때 적용되는 기본값.

**구조적 기본값**:

| 규칙 | 기본값 | 근거 |
|------|--------|------|
| God Object 임계값 | 15+ 메서드 OR 10+ 의존성 | 인지 부하 한계 |
| God Function 임계값 | 50+ 줄 OR 4+ 중첩 | 스크린 1개에 들어오는 범위 |
| 중복 임계값 | 3+ 동일 블록 | 추상화가 정당화되는 시점 |
| 파일 크기 | 200-400줄 일반, 800줄 최대 | 인지 부하 한계 |
| 테스트 전략 | 통합 테스트 우선 | 실제 시스템 검증이 가장 높은 가치 |
| 에러 처리 | 명시적 실패 | 조용한 에러 억제 금지 |
| 불변성 | 새 객체 생성 | 상태 변이 금지 |

**특성**:
- 범용 (모든 프로젝트에 적용)
- 가장 낮은 우선순위
- 상위 tier에 의해 자유롭게 오버라이드

---

## Conflict Resolution

### 규칙

1. **상위 tier가 항상 승리**: Tier 1 > Tier 1.5 > Tier 2 > Tier 3
2. **같은 tier 내**: 더 구체적인 규칙이 승리
3. **동일 구체성**: 나중에 정의된 규칙이 승리
4. **모호한 경우**: 인간에게 질문

### 예시

**상황**: 금융 프로젝트에서 단위 테스트와 통합 테스트 전략이 충돌

```
Tier 3 (기본): 통합 테스트 우선
Tier 1.5 (도메인): test_strategy: integration_first
Tier 2 (프로젝트): "모든 유틸리티 함수에 단위 테스트 필수"
```

결과: 유틸리티 함수는 단위 테스트 (Tier 2), 나머지는 통합 테스트 (Tier 1.5).
Tier 2가 구체적 범위(유틸리티 함수)를 지정하므로, 해당 범위에서 Tier 1.5를 오버라이드.

**상황**: 사용자가 "성능 우선" 지시, 도메인 프로필은 "가독성 우선"

```
Tier 1 (사용자): "성능을 우선해"
Tier 1.5 (도메인): code_style: readability_first
```

결과: 성능 우선 (Tier 1이 항상 승리).

---

## QR Integration

QR이 발견 사항을 보고할 때, 각 발견의 근거가 되는 tier를 명시한다:

```
### [GOD_FUNCTION SHOULD]: processOrder() exceeds 50 lines
- Location: src/orders.py:42
- Source: Tier 3 (structural default: function < 50 lines)
- Issue: Function is 87 lines with 5 nesting levels
- Fix: Extract validation and notification into separate functions
```

이를 통해 사용자가 "이 규칙은 우리 프로젝트에서 적합하지 않다"고 판단하면,
상위 tier에서 오버라이드할 수 있다.

---

## Documentation Requirements

### CLAUDE.md (순수 인덱스)

- 토큰 예산: ~200 토큰
- 내용: WHAT + WHEN 테이블 (파일명, 언제 읽는지)
- 아키텍처 설명 금지 → README.md로

### README.md (보이지 않는 지식)

- 토큰 예산: ~500 토큰
- 내용: 코드에서 발견할 수 없는 지식
- 테스트: "개발자가 소스 코드를 읽으면 알 수 있는가?" → 알 수 있으면 README에 넣지 않음
- 구조: Overview, Architecture, Design Decisions, Invariants

### 함수 문서

- 토큰 예산: ~100 토큰
- "use when..." 트리거 포함 (LLM이 언제 이 함수를 참조해야 하는지)
- 함수명을 독스트링에서 반복하지 않음

### 모듈 문서

- 토큰 예산: ~150 토큰
- 모듈의 책임 범위만 기술
- 구현 상세 금지
