# Collection Guide

## 수집 전략: 최소 구현부터

3가지 수집 방법을 단계적으로 도입한다.
처음부터 자동화하지 않는다. 수동 수집으로 시작하여 패턴을 파악한 뒤 자동화한다.

---

## 방법 1: 수동 세션 로그 (즉시 시작 가능)

### 절차

1. 세션 시작 시 `templates/session-log.json`을 복사
2. `session_id`, `date`, `project`, `workflow_tier`, `domain_profile` 기입
3. 작업 진행
4. 세션 종료 시 나머지 필드 기입:
   - `files_changed`: `git diff --stat` 결과에서 파일 수
   - `tokens.total`: Claude Code 세션 종료 시 표시되는 토큰 수
   - `qr_iterations`: QR 실행 시 기록 (Micro면 빈 배열)
   - `rework_count`: 같은 파일을 2회 이상 편집한 횟수
   - `notes`: 특이사항
5. `data/sessions/` 에 저장

### 파일명 규칙

```
{date}-{작업명-kebab-case}.json
```

예시: `2026-03-15-auth-jwt.json`

### 토큰 수집 방법

Claude Code 세션 종료 시 표시되는 토큰 정보를 기록:
- 전체 토큰이 표시되면 `tokens.total`에 기록
- 세부 분해(input/output/cache)가 보이면 함께 기록
- 보이지 않으면 `tokens.total`만 기록, 나머지는 0

---

## 방법 2: ccusage 연동 (방법 1 이후)

### 사전 조건

```bash
# ccusage 설치 확인
which ccusage || npm install -g ccusage
```

### 세션 토큰 자동 추출

```bash
# 오늘의 세션별 토큰
ccusage --daily --format json

# 특정 프로젝트의 세션
ccusage --session --project "backend-api" --format json
```

### 활용

- 방법 1의 `tokens` 필드를 자동으로 채울 수 있음
- `input`, `output`, `cache_read`, `cache_create` 분해 가능
- 모델별 토큰 분포 확인 가능

### 한계

- QR 반복 횟수, 재작업 횟수는 ccusage로 수집 불가
- 워크플로우 tier, 도메인 프로필은 수동 기록 필요
- ccusage는 비용 측면만 커버, 품질 측면은 별도

---

## 방법 3: cc-history JSONL 파서 (데이터 충분 시)

### 데이터 위치

```
~/.claude/projects/{encoded-project-path}/*.jsonl
```

경로 인코딩: `/Users/user/project` → `-Users-user-project`

### JSONL 구조

각 줄은 하나의 메시지:

```json
{
  "type": "assistant",
  "uuid": "abc-123",
  "parentUuid": "xyz-789",
  "timestamp": "2026-03-15T10:30:00Z",
  "message": {
    "role": "assistant",
    "content": [...],
    "usage": {
      "input_tokens": 1500,
      "output_tokens": 800,
      "cache_read_input_tokens": 500,
      "cache_creation_input_tokens": 200
    }
  }
}
```

### 추출 가능 메트릭

**QR 반복 감지**:
- 같은 파일에 대한 Edit 도구 호출이 연속으로 발생하면 재작업
- `tool_use` 블록에서 `Edit` + 동일 `file_path`를 추적

**스킬 사용 패턴**:
- `python3 -m skills\.([a-z_]+)\.` 패턴으로 스킬 호출 추출
- 서브에이전트 호출은 `Task` 도구 사용으로 감지

**모델별 토큰 분포**:
- `message.model` 필드에서 모델 식별
- 모델별 `usage` 합산

### 파싱 예시 (jq)

```bash
# 세션의 총 토큰 계산
cat session.jsonl | jq -s '
  [.[] | select(.type == "assistant") | .message.usage]
  | {
      input: (map(.input_tokens) | add),
      output: (map(.output_tokens) | add),
      cache_read: (map(.cache_read_input_tokens // 0) | add),
      cache_create: (map(.cache_creation_input_tokens // 0) | add)
    }
  | . + {total: (.input + .output)}
'

# 파일별 수정 횟수 (재작업 감지)
cat session.jsonl | jq -r '
  select(.type == "assistant")
  | .message.content[]?
  | select(.type == "tool_use" and .name == "Edit")
  | .input.file_path
' | sort | uniq -c | sort -rn
```

---

## 수집 로드맵

```
즉시        방법 1 (수동 세션 로그) 시작
            └─ 5개 세션 축적

5개 세션 후  방법 2 (ccusage) 연동
            └─ tokens 필드 자동화
            └─ 10개 세션 축적

10개 세션 후 첫 번째 분석 수행
            └─ 워크플로우별 비교
            └─ 개선 방향 도출

필요 시     방법 3 (JSONL 파서) 도입
            └─ QR 반복/재작업 자동 감지
            └─ 스킬 사용 패턴 분석
```
