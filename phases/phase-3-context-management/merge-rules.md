# 결정론적 병합 규칙

## 핵심 원칙

**모든 병합은 LLM 호출 없이 결정론적으로 수행된다.**

LLM 기반 병합의 문제점 (Context Collapse):
- 반복 요약 시 세부 정보가 점진적으로 소실
- 환각이 복리로 누적 (hallucination compounding)
- 동일 입력에 대해 비결정적 출력

규칙 기반 병합은 정보 보존을 보장하고, 동일 입력에 항상 동일 출력을 생성한다.

---

## 필드별 병합 규칙

### 1. `files_changed` — 같은 경로면 교체, 다른 경로면 추가

**규칙**: `path`를 키로 사용. 동일 경로의 엔트리가 존재하면 최신 것으로 **교체**. 새 경로는 **추가**.

**근거**: 같은 파일에 대한 이전 변경 내역은 최신 상태로 대체해도 충분하다. 파일의 "현재 상태"가 중요하지, 변경 이력 전체가 필요한 것은 아니다.

**알고리즘**:
```
function merge_files_changed(accumulated, new_entry):
    index = {}  // path → entry 매핑

    for entry in accumulated:
        index[entry.path] = entry

    for entry in new_entry:
        if entry.action == "deleted":
            // 삭제된 파일은 accumulated에서도 제거
            delete index[entry.path]
        else:
            // 교체 또는 추가
            index[entry.path] = entry

    return values(index)
```

**예시 — Before**:
```json
{
  "files_changed": [
    {"path": "src/auth.py", "action": "created", "summary": "기본 인증 모듈 생성"},
    {"path": "src/models/user.py", "action": "created", "summary": "User 모델 정의"}
  ]
}
```

**M4에서 새 델타 엔트리**:
```json
{
  "files_changed": [
    {"path": "src/auth.py", "action": "modified", "summary": "JWT 검증 로직 추가, 토큰 만료 처리"},
    {"path": "src/api/routes.py", "action": "created", "summary": "라우트 정의"}
  ]
}
```

**예시 — After (병합 결과)**:
```json
{
  "files_changed": [
    {"path": "src/auth.py", "action": "modified", "summary": "JWT 검증 로직 추가, 토큰 만료 처리"},
    {"path": "src/models/user.py", "action": "created", "summary": "User 모델 정의"},
    {"path": "src/api/routes.py", "action": "created", "summary": "라우트 정의"}
  ]
}
```

> `src/auth.py`는 최신 엔트리로 교체됨. `src/models/user.py`는 유지. `src/api/routes.py`는 새로 추가.

---

### 2. `decisions` — 항상 추가 (절대 삭제하지 않음)

**규칙**: 새 결정을 누적 목록 끝에 **추가**. 기존 결정은 어떤 경우에도 **삭제하지 않음**.

**근거**: 결정은 프로젝트의 설계 이력이다. 나중에 "왜 이렇게 했는가"를 추적하기 위해 모든 결정을 보존해야 한다. 철회된 결정도 삭제하지 않고, 새 결정으로 대체 사실을 기록한다.

**중복 판정**: `decision` 필드의 정확한 문자열 일치(exact match)로만 중복 판단. 유사하지만 다른 표현은 별도 결정으로 취급.

**알고리즘**:
```
function merge_decisions(accumulated, new_entry):
    existing_keys = set(d.decision for d in accumulated)

    for decision in new_entry:
        if decision.decision not in existing_keys:
            accumulated.append(decision)
            existing_keys.add(decision.decision)

    return accumulated
```

**예시 — Before**:
```json
{
  "decisions": [
    {"decision": "JWT > 세션", "rationale": "무상태 우선"}
  ]
}
```

**M5에서 새 결정**:
```json
{
  "decisions": [
    {"decision": "PostgreSQL > MongoDB", "rationale": "ACID 보장 필수, 트랜잭션 의존적 결제 로직"},
    {"decision": "JWT > 세션", "rationale": "무상태 우선"}
  ]
}
```

**예시 — After**:
```json
{
  "decisions": [
    {"decision": "JWT > 세션", "rationale": "무상태 우선"},
    {"decision": "PostgreSQL > MongoDB", "rationale": "ACID 보장 필수, 트랜잭션 의존적 결제 로직"}
  ]
}
```

> `JWT > 세션`은 이미 존재하므로 무시. `PostgreSQL > MongoDB`만 추가.

---

### 3. `lessons` — 중복 제거 후 추가

**규칙**: 기존 교훈과 **정규화된 문자열 유사도**를 비교하여 중복 여부 판정. 임계값 이상이면 중복으로 간주하고 추가하지 않음.

**유사도 판정 (LLM 없이)**:
1. 양쪽 문자열을 정규화: 소문자화, 구두점 제거, 공백 정규화
2. 단어 집합(bag of words) 생성
3. Jaccard 유사도 계산: `|A ∩ B| / |A ∪ B|`
4. 임계값: **0.6 이상**이면 중복으로 판정

**알고리즘**:
```
function normalize(text):
    return lowercase(remove_punctuation(collapse_whitespace(text)))

function jaccard(a, b):
    words_a = set(split(normalize(a)))
    words_b = set(split(normalize(b)))
    intersection = words_a & words_b
    union = words_a | words_b
    if len(union) == 0: return 1.0
    return len(intersection) / len(union)

function merge_lessons(accumulated, new_entry):
    THRESHOLD = 0.6

    for lesson in new_entry:
        is_duplicate = false
        for existing in accumulated:
            if jaccard(lesson, existing) >= THRESHOLD:
                is_duplicate = true
                break

        if not is_duplicate:
            accumulated.append(lesson)

    return accumulated
```

**예시 — Before**:
```json
{
  "lessons": [
    "bcrypt 라이브러리가 M1에서 이미 설치됨 — 추가 의존성 불필요",
    "PyJWT와 jwt 패키지가 충돌함 — PyJWT만 사용할 것"
  ]
}
```

**새 교훈**:
```json
{
  "lessons": [
    "bcrypt가 이미 설치되어 있으므로 별도 설치 불필요",
    "Stripe 웹훅은 반드시 서명 검증 필요"
  ]
}
```

**예시 — After**:
```json
{
  "lessons": [
    "bcrypt 라이브러리가 M1에서 이미 설치됨 — 추가 의존성 불필요",
    "PyJWT와 jwt 패키지가 충돌함 — PyJWT만 사용할 것",
    "Stripe 웹훅은 반드시 서명 검증 필요"
  ]
}
```

> 첫 번째 새 교훈은 기존 것과 Jaccard 유사도 ≥ 0.6이므로 중복 판정, 추가 안 됨. 두 번째는 새로운 내용이므로 추가.

---

### 4. `unresolved` — 해결된 항목 제거, 새 항목 추가

**규칙**: `next_steps` 완료 또는 `files_changed`에 관련 파일이 나타나면 해결된 것으로 간주하고 **제거**. 새 미해결 항목은 **추가**.

**해결 판정 기준** (순서대로 적용):
1. **명시적 해결**: 새 델타의 `next_steps` 또는 `files_changed.summary`에 미해결 항목의 키워드가 포함되면 해결로 판정
2. **키워드 매칭**: 미해결 항목의 핵심 키워드(명사 + 동사)를 추출하고, `files_changed.summary`의 키워드와 비교. Jaccard 유사도 ≥ 0.4이면 해결로 판정

**알고리즘**:
```
function merge_unresolved(accumulated, new_delta):
    resolved = set()

    // files_changed의 summary와 키워드 매칭
    change_summaries = join(" ", [f.summary for f in new_delta.files_changed])

    for item in accumulated:
        if jaccard(normalize(item), normalize(change_summaries)) >= 0.4:
            resolved.add(item)

    // 해결된 항목 제거
    result = [item for item in accumulated if item not in resolved]

    // 새 미해결 항목 추가 (중복 체크)
    for item in new_delta.unresolved:
        if not any(jaccard(item, existing) >= 0.6 for existing in result):
            result.append(item)

    return result
```

**예시 — Before**:
```json
{
  "unresolved": [
    "토큰 갱신(refresh token) 전략 미확정",
    "RBAC 세부 권한 모델 미정의",
    "API Rate limiting 미구현"
  ]
}
```

**M6 델타 엔트리**:
```json
{
  "files_changed": [
    {"path": "src/auth/refresh.py", "action": "created", "summary": "리프레시 토큰 발급 및 갱신 엔드포인트 구현"}
  ],
  "unresolved": [
    "리프레시 토큰 탈취 시 무효화 전략 미정의"
  ]
}
```

**예시 — After**:
```json
{
  "unresolved": [
    "RBAC 세부 권한 모델 미정의",
    "API Rate limiting 미구현",
    "리프레시 토큰 탈취 시 무효화 전략 미정의"
  ]
}
```

> "토큰 갱신 전략 미확정"은 `refresh.py` 생성으로 해결 판정되어 제거. 새 미해결 항목 추가.

---

### 5. `next_steps` — 완료된 항목 제거, 새 항목 추가

**규칙**: `files_changed`에 관련 파일이 나타나면 완료로 간주하고 **제거**. 새 다음 단계는 **추가**.

**완료 판정 기준**: `unresolved`의 해결 판정과 동일한 키워드 매칭 방식 사용 (Jaccard 유사도 ≥ 0.4).

**알고리즘**:
```
function merge_next_steps(accumulated, new_delta):
    completed = set()

    change_summaries = join(" ", [f.summary for f in new_delta.files_changed])

    for step in accumulated:
        if jaccard(normalize(step), normalize(change_summaries)) >= 0.4:
            completed.add(step)

    // 완료된 항목 제거
    result = [step for step in accumulated if step not in completed]

    // 새 항목 추가 (중복 체크)
    for step in new_delta.next_steps:
        if not any(jaccard(step, existing) >= 0.6 for existing in result):
            result.append(step)

    return result
```

**예시 — Before**:
```json
{
  "next_steps": [
    "토큰 갱신 엔드포인트 구현 (POST /auth/refresh)",
    "RBAC 권한 매트릭스 설계",
    "인증 미들웨어 통합 테스트 작성"
  ]
}
```

**M6 델타 엔트리**:
```json
{
  "files_changed": [
    {"path": "src/auth/refresh.py", "action": "created", "summary": "리프레시 토큰 발급 및 갱신 엔드포인트 구현"},
    {"path": "tests/test_auth_middleware.py", "action": "created", "summary": "인증 미들웨어 통합 테스트 12건 작성"}
  ],
  "next_steps": [
    "리프레시 토큰 회전(rotation) 정책 구현",
    "환불 API 설계"
  ]
}
```

**예시 — After**:
```json
{
  "next_steps": [
    "RBAC 권한 매트릭스 설계",
    "리프레시 토큰 회전(rotation) 정책 구현",
    "환불 API 설계"
  ]
}
```

> "토큰 갱신 엔드포인트"와 "인증 미들웨어 통합 테스트"는 `files_changed`와 매칭되어 완료 처리. 새 항목 2개 추가.

---

### 6. `context_snapshot` — 항상 최신으로 교체

**규칙**: 새 델타의 `context_snapshot`이 존재하면 기존 것을 **완전히 교체**. 존재하지 않으면 이전 값 유지.

**근거**: 스냅샷은 "현재 시점"의 상태만 의미가 있다. 이력은 불필요.

---

## 충돌 해결 규칙

### 상황 1: 같은 파일이 "created"와 "deleted" 모두로 나타남

**규칙**: 타임스탬프가 더 최신인 엔트리 우선. 타임스탬프가 같으면 `deleted` 우선 (보수적 접근).

### 상황 2: 결정이 이전 결정과 모순됨

**규칙**: 삭제하지 않고 **양쪽 모두 유지**. 새 결정의 `rationale`에 이전 결정 변경 사유가 포함되어야 함.

예시:
```json
[
  {"decision": "MongoDB 사용", "rationale": "초기 프로토타입 유연성"},
  {"decision": "PostgreSQL > MongoDB", "rationale": "M4에서 ACID 필요성 확인. MongoDB에서 마이그레이션"}
]
```

### 상황 3: 동일 unresolved 항목이 해결/미해결 동시 판정

**규칙**: 해결 판정이 우선. 해결된 것으로 처리하고 제거.

### 상황 4: 병합 순서에 따라 결과가 달라질 수 있는 경우

**규칙**: 항상 타임스탬프 순서(오래된 것 → 최신)로 병합. 타임스탬프가 같으면 milestone 번호 순.

---

## 엣지 케이스

### 빈 필드

- 새 델타의 필드가 빈 배열 `[]`이면: 기존 누적 값 유지 (아무것도 추가/제거하지 않음)
- 새 델타의 필드가 누락(undefined)이면: 기존 누적 값 유지
- 누적 값과 새 델타 모두 비어있으면: 빈 배열 `[]` 유지

### 매우 긴 문자열

- `maxLength`를 초과하는 항목은 병합 전에 잘림(truncation) 처리
- 잘린 문자열 끝에 `...` 추가

### 특수 문자 / 다국어

- 유사도 비교 시 영문은 소문자 변환, 한국어는 그대로 유지
- 코드 스니펫(`backtick`으로 감싸진 부분)은 유사도 비교에서 제외

---

## 토큰 예산 및 가지치기 전략

### 최대 누적 컨텍스트 크기

| 필드 | 최대 항목 수 | 예상 토큰 | 근거 |
|------|-------------|----------|------|
| `files_changed` | 200 | ~4,000 | 대규모 프로젝트 기준 |
| `decisions` | 100 | ~5,000 | 결정당 ~50 토큰 |
| `lessons` | 50 | ~2,000 | 교훈당 ~40 토큰 |
| `unresolved` | 30 | ~600 | 활성 이슈만 유지 |
| `next_steps` | 20 | ~400 | 당장 필요한 것만 |
| **합계** | - | **~12,000** | 전체 컨텍스트의 10-15% |

### 예산 초과 시 가지치기 순서

예산을 초과하면 아래 순서대로 가지치기:

1. **`lessons`**: 가장 오래된 것부터 제거 (오래된 교훈일수록 현재 맥락과 무관할 확률 높음)
2. **`files_changed`**: 마지막 수정이 가장 오래된 파일부터 제거 (최근 변경 파일이 더 중요)
3. **`next_steps`**: 가장 오래된 것부터 제거 (오래 머무른 next_step은 사실상 backlog)
4. **`decisions`**: **절대 가지치기하지 않음**. 결정 이력은 항상 보존
5. **`unresolved`**: **절대 가지치기하지 않음**. 활성 이슈를 놓치면 안 됨

### 가지치기 알고리즘

```
function prune_if_needed(accumulated, token_budget):
    current_tokens = estimate_tokens(accumulated)

    if current_tokens <= token_budget:
        return accumulated

    // 1단계: lessons 가지치기 (최소 10개 유지)
    while current_tokens > token_budget and len(accumulated.lessons) > 10:
        accumulated.lessons.pop(0)  // 가장 오래된 것 제거
        current_tokens = estimate_tokens(accumulated)

    // 2단계: files_changed 가지치기 (최소 50개 유지)
    if current_tokens > token_budget:
        sort_by_last_modified(accumulated.files_changed)  // 오래된 순
        while current_tokens > token_budget and len(accumulated.files_changed) > 50:
            accumulated.files_changed.pop(0)
            current_tokens = estimate_tokens(accumulated)

    // 3단계: next_steps 가지치기 (최소 5개 유지)
    if current_tokens > token_budget:
        while current_tokens > token_budget and len(accumulated.next_steps) > 5:
            accumulated.next_steps.pop(0)
            current_tokens = estimate_tokens(accumulated)

    return accumulated
```

---

## 전체 병합 파이프라인

```
function merge_delta(accumulated_context, new_delta):
    // 1. 필드별 병합
    result = {
        files_changed: merge_files_changed(accumulated_context.files_changed, new_delta.files_changed),
        decisions: merge_decisions(accumulated_context.decisions, new_delta.decisions),
        lessons: merge_lessons(accumulated_context.lessons, new_delta.lessons),
        unresolved: merge_unresolved(accumulated_context.unresolved, new_delta),
        next_steps: merge_next_steps(accumulated_context.next_steps, new_delta),
        context_snapshot: new_delta.context_snapshot ?? accumulated_context.context_snapshot
    }

    // 2. 예산 체크 및 가지치기
    result = prune_if_needed(result, TOKEN_BUDGET)

    // 3. 검증
    validate_no_information_loss(accumulated_context.decisions, result.decisions)
    validate_no_information_loss(accumulated_context.unresolved, result.unresolved)

    return result
```
