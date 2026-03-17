---
name: do-review
description: |
  todo 폴더의 코드 리뷰 작업을 sub-agent로 실행한다.
  PR을 clone/checkout하고, 변경사항을 분석하여 리뷰 결과를 생성한다.
trigger-keywords: do-review, 리뷰 실행, start review, run review
user-invocable: true
---

## Instructions

todo 폴더의 코드 리뷰 작업을 실행한다. 인자로 특정 파일명이 주어지면 해당 건만, 없으면 가장 오래된 todo부터 진행한다.

### Step 1: 대상 리뷰 선택

**인자가 있는 경우**: 해당 파일명의 todo를 읽는다.
**인자가 없는 경우**: `review_list_todo`를 호출하여 가장 오래된 항목을 선택한다.

todo가 없으면:
```
처리할 리뷰 작업이 없습니다. `/check-reviews`로 먼저 확인하세요.
```
출력 후 종료한다.

### Step 2: todo 문서 읽기

선택된 todo 문서를 Read 도구로 읽어 repo, PR 번호, 변경 파일 목록을 파싱한다.

### Step 3: PR 환경 셋업

sub-agent(code-reviewer 타입)를 실행하여 리뷰를 진행한다.
Agent에게 전달할 프롬프트:

```
다음 PR에 대한 코드 리뷰를 수행하세요.

## PR 정보
- Repository: {repo}
- PR: #{pr_number}
- Branch: {head_branch} -> {base_branch}

## 작업 순서

1. 레포지토리를 clone하고 PR 브랜치를 checkout합니다:
   ```bash
   gh repo clone {repo} /tmp/review-{safe_repo}-{pr_number}
   cd /tmp/review-{safe_repo}-{pr_number}
   gh pr checkout {pr_number}
   ```

2. PR의 전체 diff를 확인합니다:
   ```bash
   gh pr diff {pr_number}
   ```

3. 변경된 파일들을 분석합니다. 다음 관점에서 리뷰하세요:
   - 코드 정확성 및 로직 오류
   - 보안 취약점 (입력 검증, 인젝션, 인증 등)
   - 성능 이슈
   - 코드 스타일 및 가독성
   - 테스트 커버리지

4. 리뷰 결과를 다음 형식으로 작성합니다:
   ## Review Summary
   - 전체 평가 (approve / request changes / comment)
   - 주요 발견사항 요약

   ## Findings
   각 발견사항:
   - 파일명:라인번호
   - 심각도 (critical / warning / suggestion)
   - 설명
   - 수정 제안

   ## Files Reviewed
   각 파일별 한줄 요약
```

### Step 4: 리뷰 결과 저장

sub-agent의 결과를 todo 문서에 추가하여 업데이트한다.

todo 문서 하단에 결과를 append:
```markdown
---

## Review Result

- **Reviewed at**: {timestamp}
- **Verdict**: {approve/request_changes/comment}

{sub-agent 리뷰 결과}
```

### Step 5: 상태 업데이트

리뷰 완료 후:
1. `review_mark_done`을 호출하여 pending → done으로 이동
2. 사용자에게 결과 요약 출력

```
## 리뷰 완료: {repo}#{pr_number}

- 판정: {verdict}
- 주요 발견: {findings_count}건 (critical: N, warning: N, suggestion: N)

리뷰 결과: {todo_file_path}

GitHub에 리뷰를 게시하려면:
  gh pr review {pr_number} --repo {repo} --comment --body-file {result_file}
```

### Step 6: 다음 리뷰 제안

대기 중인 todo가 더 있으면:
```
남은 리뷰: {remaining_count}건. 계속하려면 `/do-review`를 실행하세요.
```
