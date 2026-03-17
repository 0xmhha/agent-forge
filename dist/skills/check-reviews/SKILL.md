---
name: check-reviews
description: |
  MCP 서버에서 신규 코드 리뷰 요청을 확인하고, 대기 중인 리뷰를 정리한다.
  신규 요청이 있으면 todo 문서를 생성하여 작업 준비를 완료한다.
trigger-keywords: check-reviews, 리뷰 확인, review check, pending reviews
user-invocable: true
---

## Instructions

신규 코드 리뷰 요청을 확인하고 작업 문서를 준비한다.

### Step 1: 대기 중인 리뷰 확인

MCP 도구 `review_list_pending`을 호출하여 신규 리뷰 요청 목록을 가져온다.

결과가 비어 있으면:
```
신규 코드 리뷰 요청이 없습니다.
```
출력 후 종료한다.

### Step 2: 기존 todo 확인

MCP 도구 `review_list_todo`를 호출하여 이미 생성된 todo 문서 목록을 가져온다.

### Step 3: 신규 요청에 대해 todo 생성

pending 목록에서 아직 todo가 없는 항목을 찾아 `review_create_todo`를 호출한다.

각 todo 생성 시 출력:
```
📋 새 리뷰 작업 생성: {repo}#{pr_number}
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
