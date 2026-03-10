# Quality Review Rules

## Severity Classification

리뷰 발견 사항을 3단계 심각도로 분류한다.
각 심각도는 차단 수준과 조치 방식이 다르다.

### MUST (절대)

놓치면 복구 불가능한 것. 모든 반복에서 차단.

| 카테고리 | 설명 | 예시 |
|----------|------|------|
| SECURITY_VIOLATION | 보안 취약점 | SQL 인젝션, XSS, 하드코딩된 시크릿, 미검증 입력 |
| DATA_LOSS_RISK | 데이터 손실 위험 | 트랜잭션 없는 상태 변경, 백업 없는 삭제 |
| DECISION_LOG_MISSING | 결정 근거 누락 | 아키텍처 선택의 이유가 코드/문서 어디에도 없음 |
| CONTRACT_VIOLATION | 인터페이스 계약 위반 | API 응답 스키마 불일치, 타입 불일치 |
| TEMPORAL_CONTAMINATION | 시간적 오염 | 코멘트가 변경 이력을 노출 (Temporal 규칙 위반) |

**판정 기준**: "이것이 프로덕션에 배포되면 복구 가능한가?" → 불가능하면 MUST.

### SHOULD (권장)

유지보수 부채. 즉시 위험하지 않지만 누적되면 문제.

| 카테고리 | 설명 | 예시 |
|----------|------|------|
| GOD_OBJECT | 과도한 책임 집중 | 15+ 메서드, 10+ 의존성, 혼합된 관심사 |
| GOD_FUNCTION | 과도하게 긴 함수 | 50+ 줄, 4+ 중첩, 혼합된 추상화 수준 |
| DUPLICATE_LOGIC | 중복 로직 | 파일 내 복사-붙여넣기, 추상화 누락 |
| INCONSISTENT_ERROR | 불일치 에러 처리 | 같은 모듈에서 예외와 에러코드 혼용 |
| CONVENTION_VIOLATION | 프로젝트 규약 위반 | 문서화된 규약과 다른 패턴 사용 |
| TESTING_GAP | 테스트 전략 위반 | 크리티컬 경로에 테스트 없음 |

**판정 기준**: "이것이 6개월 후 유지보수를 어렵게 하는가?" → 그렇다면 SHOULD.

### COULD (선택)

자동 수정 가능하거나, 미미한 영향.

| 카테고리 | 설명 | 예시 |
|----------|------|------|
| DEAD_CODE | 사용되지 않는 코드 | 호출자 없는 함수, 도달 불가 분기 |
| FORMATTER_FIXABLE | 포매터로 수정 가능 | 들여쓰기, 줄바꿈, 공백 |
| MINOR_INCONSISTENCY | 경미한 불일치 | 네이밍 스타일의 사소한 차이 |

**판정 기준**: "이것이 린터나 포매터로 자동 수정 가능한가?" → 가능하면 COULD.

---

## Iteration Escalation Rules

QR 반복 시 심각도별 차단 수준을 조정하여 무한 루프를 방지한다.

| 반복 | 차단 대상 | 근거 |
|------|----------|------|
| iter 1-2 | MUST + SHOULD + COULD | 첫 리뷰에서 최대한 많이 포착 |
| iter 3-4 | MUST + SHOULD | COULD는 부채로 수용, 핵심에 집중 |
| iter 5+ | MUST만 | 무한 루프 방지, 절대적 위험만 차단 |

**에스컬레이션 규칙**:
- iter 3에서 동일 MUST가 반복되면: 문제를 재정의하거나, 상위 모델로 에스컬레이션
- iter 5에서도 MUST가 해결되지 않으면: 인간 개입 요청

---

## Review Protocol

### 실행 순서

```
1. 컨텍스트 수집
   - 프로젝트 문서 (CLAUDE.md, README.md) 읽기
   - 도메인 프로필 읽기 (있는 경우)
   - 변경 범위 파악

2. 사실 수집
   - 코드/문서에서 관찰 가능한 사실만 수집
   - 의도 추측 금지

3. 규칙 적용
   - MUST 판정: 열린 질문으로 검증 ("이것이 프로덕션에서 어떤 결과를 초래하는가?")
   - SHOULD 판정: 프로젝트 규약 참조
   - COULD 판정: 자동 수정 가능 여부 확인

4. 이중 경로 검증 (MUST에만 적용)
   - 경로 A: "이것이 문제인 이유는?"
   - 경로 B: "이것이 문제가 아닌 이유는?"
   - 양쪽 모두 설득력 있으면: MUST 유지
   - B가 더 설득력 있으면: SHOULD로 하향
```

### 출력 형식

```
VERDICT: [PASS | PASS_WITH_CONCERNS | NEEDS_CHANGES]

FINDINGS:
### [CATEGORY SEVERITY]: [Title]
- Location: [file:line]
- Issue: [description]
- Impact: [consequence]
- Fix: [action]

REASONING: [max 30 words]
```

---

## Intent Markers

개발자가 의도적으로 규칙을 위반하는 경우, 마커로 표시하면 QR이 해당 검사를 건너뛴다.

**형식**: `:MARKER: [what]; [why]`

| 마커 | 용도 | 예시 |
|------|------|------|
| `:PERF:` | 성능 최적화 | `:PERF: unchecked bounds; hot loop, profiled safe` |
| `:UNSAFE:` | 안전성 트레이드오프 | `:UNSAFE: raw pointer; FFI boundary, caller guarantees lifetime` |
| `:SCHEMA:` | 데이터 계약 예외 | `:SCHEMA: field unused; migration pending, remove in v2.1` |

**QR 처리**:
1. 마커 감지
2. 형식 검증 (세미콜론 있는가, why가 비어있지 않은가)
3. 유효: 관련 검사 건너뜀
4. 무효: MUST (MARKER_INVALID) 보고
