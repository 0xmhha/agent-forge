---
name: pr-review
description: |
  GitHub PR을 클론하고 프로젝트별 분석 도구를 자동 감지하여 체계적인 코드 리뷰를 수행한다.
  repo와 PR 번호를 인자로 받아 격리된 작업 디렉토리에서 lint, test, 코드 분석을 실행한다.
  리뷰 완료 후 구조화된 보고서를 생성하며, GitHub에 코멘트 게시도 가능하다.
trigger-keywords: pr-review, PR 리뷰, review PR, pull request review, 코드 리뷰
user-invocable: true
---

## Instructions

GitHub PR에 대한 체계적인 코드 리뷰를 수행한다.

**사용법**: `/pr-review {owner/repo} {pr_number}`
**예시**: `/pr-review stable-net/go-stablenet 42`

### Step 1: 입력 파싱

인자에서 repository와 PR 번호를 파싱한다.

- 인자가 없으면 사용자에게 질문:
  ```
  리뷰할 PR 정보를 입력해주세요:
  - Repository (owner/repo):
  - PR 번호:
  ```

- 인자가 부족하면 누락된 정보를 질문한다.

파싱 결과:
```
repo = "{owner}/{repo}"
pr_number = {number}
safe_name = "{repo}-pr-{number}"    # 디렉토리명용
work_dir = "/tmp/agent-forge-reviews/{safe_name}"
```

### Step 2: PR 정보 사전 수집

PR의 기본 정보를 먼저 수집하여 리뷰 범위를 파악한다:

```bash
gh pr view {pr_number} --repo {repo} --json title,body,baseRefName,headRefName,files,additions,deletions,state
```

PR이 존재하지 않거나 이미 closed/merged 상태면 사용자에게 알린다.

수집된 정보를 요약 출력:

```
## PR #{pr_number}: {title}
- Branch: {head} → {base}
- 변경: +{additions}/-{deletions}, {files_count}개 파일
- 상태: {state}

리뷰를 시작합니다...
```

### Step 3: 작업 환경 준비

격리된 작업 디렉토리에 repo를 클론하고 PR을 체크아웃한다:

```bash
# 기존 디렉토리가 있으면 정리
rm -rf {work_dir}
mkdir -p {work_dir}

# 클론 및 체크아웃
gh repo clone {repo} {work_dir} -- --depth=50
cd {work_dir}
gh pr checkout {pr_number}
```

클론 실패 시:
- 인증 문제: `gh auth status` 확인 안내
- 권한 문제: 리포지토리 접근 권한 확인 안내

### Step 4: 프로젝트 분석 도구 감지

클론된 프로젝트에서 사용 가능한 분석 도구를 자동 감지한다:

Glob 도구로 다음 파일을 탐색:

```
감지 대상:
  .golangci.yml, .golangci.yaml     → tool_lint = "golangci-lint"
  .eslintrc.*, eslint.config.*      → tool_lint = "eslint"
  pyproject.toml (ruff 섹션)        → tool_lint = "ruff"
  Cargo.toml                        → tool_lint = "cargo-clippy"

  Makefile, makefile                 → make_targets 파싱 (lint, test, test-short)

  .claude/docs/REVIEW_GUIDE.md      → review_guide = true
  .claude/docs/CLAUDE_DEV_GUIDE.md  → dev_guide = true
  .claude/docs/BUILD_SOURCE_FILES.md → build_inventory = true
  .claude/commands/*review*          → review_command = true
```

감지 결과를 사용자에게 출력:

```
## 감지된 분석 도구
- [x] golangci-lint (.golangci.yml)
- [x] Makefile: lint, test-short 타겟
- [x] 프로젝트 리뷰 가이드 (.claude/docs/REVIEW_GUIDE.md)
- [x] 개발 가이드 (.claude/docs/CLAUDE_DEV_GUIDE.md)
- [ ] eslint (미감지)
```

### Step 5: pr-reviewer 에이전트 디스패치

Agent 도구를 사용하여 pr-reviewer 서브 에이전트를 디스패치한다.

에이전트에게 전달할 프롬프트를 구성한다:

```
다음 PR에 대한 코드 리뷰를 수행하세요.

## PR 정보
- Repository: {repo}
- PR: #{pr_number} - {pr_title}
- Branch: {head} → {base}
- 변경: +{additions}/-{deletions}

## 작업 디렉토리
{work_dir}

## 감지된 분석 도구
{감지 결과}

## PR 변경 파일
{files_list}

## 리뷰 지시사항

1. 작업 디렉토리로 이동하세요:
   cd {work_dir}

2. PR diff를 확인하세요:
   gh pr diff {pr_number} --repo {repo}

{리뷰 가이드가 있으면}
3. 프로젝트 리뷰 가이드를 읽으세요:
   Read: {work_dir}/.claude/docs/REVIEW_GUIDE.md
   Read: {work_dir}/.claude/docs/CLAUDE_DEV_GUIDE.md

4. 감지된 린터를 실행하세요:
{tool_lint == "golangci-lint" 이면}
   cd {work_dir} && golangci-lint run --new-from-rev={base_branch} ./...
{tool_lint == "eslint" 이면}
   cd {work_dir} && npx eslint {changed_files}
{make lint 타겟이 있으면}
   cd {work_dir} && make lint

5. 변경된 패키지의 테스트를 실행하세요:
{Go 프로젝트이면}
   cd {work_dir} && go test -short -count=1 {affected_packages}
{make test-short 타겟이 있으면}
   cd {work_dir} && make test-short

6. 변경 파일을 하나씩 Read 도구로 읽고 분석하세요:
   - 정확성: 로직 오류, 엣지 케이스
   - 보안: 입력 검증, 인젝션, 시크릿
   - 성능: 불필요한 할당, N+1, 루프 내 I/O
   - 동시성: 레이스 컨디션, 데드락
   - 스타일: 네이밍, 가독성
   - 테스트: 커버리지, 엣지 케이스 테스트
   - 설계: 결합도, 책임 분리

7. 리뷰 보고서를 다음 경로에 저장하세요:
   {work_dir}/REVIEW_REPORT.md

   형식:
   # PR Review Report
   ## Summary
   - Repository: {repo}
   - PR: #{pr_number} - {title}
   - Reviewed at: {timestamp}
   - Verdict: APPROVE / REQUEST_CHANGES / COMMENT

   ## Tool Results
   ### Lint: PASS/FAIL (N issues)
   ### Test: PASS/FAIL (passed/total)

   ## Findings
   ### Critical (N)
   #### [파일:라인] 제목
   - 관점: 정확성/보안/동시성
   - 설명: ...
   - 수정 제안: diff 형식

   ### Warning (N)
   ### Suggestion (N)

   ## Files Reviewed
   | 파일 | 변경 | 평가 | 요약 |

   ## Architecture Impact
   변경이 전체 아키텍처에 미치는 영향

8. 요약을 반환하세요.
```

에이전트를 `subagent_type: "code-reviewer"` 또는 일반 에이전트로 디스패치한다.

### Step 6: 리뷰 결과 수집

에이전트 완료 후:

1. `{work_dir}/REVIEW_REPORT.md`를 Read 도구로 읽는다
2. 결과를 사용자에게 요약 출력:

```
## PR Review Complete: {repo}#{pr_number}

- Verdict: {APPROVE / REQUEST_CHANGES / COMMENT}
- Critical: {n}건 | Warning: {n}건 | Suggestion: {n}건
- Lint: {PASS/FAIL} | Test: {PASS/FAIL}

리뷰 보고서: {work_dir}/REVIEW_REPORT.md
```

### Step 7: 후속 액션 제안

```
## 다음 단계

1. 리뷰 보고서 상세 확인:
   Read: {work_dir}/REVIEW_REPORT.md

2. GitHub에 리뷰 코멘트 게시:
   gh pr review {pr_number} --repo {repo} --comment --body-file {work_dir}/REVIEW_REPORT.md

3. 리뷰 승인:
   gh pr review {pr_number} --repo {repo} --approve

4. 변경 요청:
   gh pr review {pr_number} --repo {repo} --request-changes --body-file {work_dir}/REVIEW_REPORT.md

5. 작업 디렉토리 정리:
   rm -rf {work_dir}
```

### Step 8: 리뷰 상태 기록

리뷰 완료 상태를 기록한다:

```bash
mkdir -p .agent-forge-state/reviews
echo '{
  "repo": "{repo}",
  "pr": {pr_number},
  "verdict": "{verdict}",
  "critical": {n},
  "warning": {n},
  "suggestion": {n},
  "reviewed_at": "{timestamp}",
  "report_path": "{work_dir}/REVIEW_REPORT.md"
}' > .agent-forge-state/reviews/{safe_name}.json
```
