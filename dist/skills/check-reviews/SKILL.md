---
name: check-reviews
description: |
  workspace-mcp를 통해 Gmail과 GitHub에서 신규 코드 리뷰 요청을 병렬 수집한다.
  대기 중인 리뷰를 정리하고, 신규 요청에 대해 todo 문서를 자동 생성한다.
  workspace-mcp 서버 연결 필수.
trigger-keywords: check-reviews, 리뷰 확인, review check, pending reviews
user-invocable: true
---

## Instructions

신규 코드 리뷰 요청을 병렬로 수집하고 작업 문서를 준비한다.

### Step 1: 병렬 데이터 수집

다음 3개의 MCP 도구를 **동시에** 호출한다 (병렬 실행):

| 호출 | MCP 도구 | 목적 |
|------|----------|------|
| A | `review_list_pending` | 이미 감지된 대기 중인 리뷰 목록 |
| B | `review_list_todo` | 이미 생성된 todo 문서 목록 |
| C | `review_list_done` | 완료된 리뷰 목록 (통계용) |

> **병렬 실행 원칙**: A, B, C는 서로 독립적이므로 반드시 동시에 호출한다.
> 순차 호출은 불필요한 지연을 발생시킨다.

### Step 2: 결과 종합

병렬 호출 결과를 종합한다:
- pending 목록에서 아직 todo가 없는 항목을 식별
- 이미 todo가 있는 항목은 건너뜀

pending이 비어 있으면:
```
신규 코드 리뷰 요청이 없습니다.
```
출력 후 종료한다.

### Step 3: 신규 요청에 대해 todo 생성

pending 목록에서 아직 todo가 없는 항목을 찾아 `review_create_todo`를 호출한다.

각 todo 생성 시 출력:
```
새 리뷰 작업 생성: {repo}#{pr_number}
   파일: {todo_filename}
```

### Step 4: 요약 출력

```
## 코드 리뷰 현황

| 상태 | 건수 |
|------|------|
| 신규 대기 | {pending_count} |
| 작업 준비 완료 (todo) | {todo_count} |
| 완료 | {done_count} |

### 신규 작업 목록
{각 todo 항목의 repo, PR번호, 제목 테이블}
```

### Step 5: 리뷰 실행 제안

신규 todo가 있으면 사용자에게 제안한다:
```
리뷰를 시작하려면 `/do-review` 를 실행하세요.
특정 리뷰만 진행하려면 `/do-review {filename}` 으로 지정할 수 있습니다.
```
