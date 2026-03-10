# Temporal Rules

## Core Principle: Timeless Present

코멘트는 코드를 **처음 만나는 독자**의 관점에서 작성한다.
독자는 이전 버전을 모르고, 변경 이력을 알지 못하며, 계획 문서를 읽지 않았다.

코멘트가 설명하는 것: 코드가 **지금 무엇인지** (IS)
코멘트가 설명하지 않는 것: 코드가 **어떻게 여기에 왔는지** (WAS/BECAME)

---

## Detection Heuristics

5가지 유형의 시간적 오염과 수정 방법.

### 1. Change-Relative (변경 참조)

변경 행위 자체를 언급하는 코멘트.

| 오염 | 수정 |
|------|------|
| "Added mutex for thread safety" | "Mutex serializes concurrent access to shared cache" |
| "Fixed the null check issue" | "Null check prevents crash on missing config" |
| "Refactored to use composition" | "Composition enables independent testing of each handler" |
| "Moved from sync to async" | "Async prevents I/O blocking on the main thread" |

**감지 키워드**: added, fixed, refactored, moved, changed, updated, replaced, removed, migrated

### 2. Baseline Reference (베이스라인 참조)

이전 상태나 대안과의 비교를 언급하는 코멘트.

| 오염 | 수정 |
|------|------|
| "Replaces the old polling approach" | "Event-driven: eliminates polling overhead" |
| "Better than the previous implementation" | "O(log n) lookup via balanced tree" |
| "Unlike the legacy system" | "Each request is stateless and independently verifiable" |

**감지 키워드**: replaces, old, previous, legacy, unlike, instead of, better than, formerly

### 3. Location Directive (위치 지시)

코드 내 위치를 지시하는 코멘트. diff 구조가 위치를 인코딩하므로 불필요.

| 오염 | 수정 |
|------|------|
| "Insert before the validation step" | (삭제) |
| "Place this after the auth middleware" | (삭제) |
| "Goes in the config section" | (삭제) |

**처리**: 항상 삭제. 위치 정보는 코드 구조 자체가 전달.

### 4. Planning Artifact (계획 아티팩트)

계획 문서나 미래 작업을 참조하는 코멘트.

| 오염 | 수정 |
|------|------|
| "TODO: add retry logic later" | (삭제하거나 즉시 구현) |
| "As discussed in the design doc" | (삭제 - 코드가 자체 설명적이어야 함) |
| "Per milestone 3 requirements" | (삭제 - 요구사항은 코드에 반영됨) |
| "Placeholder for future feature" | (삭제하거나 인터페이스로 명시) |

**감지 키워드**: TODO, FIXME, later, future, placeholder, as discussed, per requirements, milestone

### 5. Intent Leakage (의도 노출)

결정 과정이나 선택 이유를 부적절하게 노출하는 코멘트.

| 오염 | 수정 |
|------|------|
| "Chose polling for reliability" | "Polling: 30% webhook failure rate in production" |
| "We decided to use JWT" | "JWT enables stateless auth across distributed services" |
| "Selected bcrypt over argon2" | "bcrypt: compatible with existing auth pipeline" |

**핵심 차이**: "왜 선택했는가" (의도) → "무엇이 이것을 정당화하는가" (사실)

---

## Application Rules

### 코멘트에 적용

모든 인라인 코멘트, 함수 독스트링, 모듈 설명에 적용.

```python
# BAD: "Added error handling for the edge case we found"
# GOOD: "Handles empty input gracefully — returns default config"

# BAD: "Refactored from the monolithic approach"
# GOOD: "Each handler processes one event type independently"
```

### 커밋 메시지에는 미적용

커밋 메시지는 본질적으로 시간적이다 (변경 이력을 기록하는 것이 목적).
Temporal 규칙은 코드 내 코멘트와 문서에만 적용.

### README.md에 적용

README의 아키텍처 설명, 설계 결정 기록에도 적용.
단, "Design Decisions" 섹션에서는 결정 과정을 기록하는 것이 목적이므로 예외.

---

## QR Integration

Temporal 위반은 **MUST (TEMPORAL_CONTAMINATION)** 심각도.

QR이 감지하면:
1. 오염 유형 식별 (5가지 중)
2. 오염된 텍스트와 수정 제안 제시
3. MUST로 보고 — 수정 전까지 다음 단계 차단

Temporal 위반이 가장 빈번한 위치:
- diff에 포함된 코멘트 (변경 행위를 설명하는 경향)
- 새로 추가된 함수의 독스트링 ("Added this function to..." 패턴)
- README 업데이트 ("Changed the approach to..." 패턴)
