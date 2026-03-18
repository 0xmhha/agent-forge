# workspace-mcp

Gmail + GitHub MCP 서버. 이메일에서 Jira 티켓을 감지하고, GitHub 이슈/PR/CI 상태를 모니터링한다.
LLM에 토큰이 노출되지 않도록 룰베이스로 동작하며, 결과만 구조화하여 반환한다.

## Quick Start

```bash
cd tools/workspace-mcp

make install  # 의존성 설치
cp .env.sample .env
# .env 파일에 GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET 입력

make setup    # OAuth 인증 (최초 1회)
make server   # MCP 서버 실행
```

> **Setup UI vs MCP 서버**: Setup UI는 OAuth 토큰을 발급·저장하는 인증 도구 (최초 1회).
> MCP 서버는 저장된 토큰으로 Gmail/GitHub API를 호출하는 도구 서버 (매 세션).

## Make 명령어

`make` 또는 `make help`로 전체 명령어를 확인할 수 있다.

| 명령 | 설명 |
|------|------|
| `make server` | MCP 서버 실행 |
| `make debug` | DEBUG 레벨로 MCP 서버 실행 |
| `make setup` | OAuth 설정 UI (최초 1회) |
| `make install` | 의존성 설치 |
| `make test` | 전체 테스트 |
| `make test-v` | 테스트 (상세 출력) |
| `make lint` | 코드 린트 |
| `make fix` | 린트 자동 수정 |
| `make log` | 실시간 로그 모니터링 (tail -f) |
| `make log-all` | 전체 로그 보기 |
| `make status` | 토큰/배치 설정/리뷰 큐 상태 확인 |
| `make clean` | 캐시/로그 정리 |

## 초기 설정: Gmail 연동

### 1. Google Cloud Console 설정

1. [console.cloud.google.com](https://console.cloud.google.com) 접속 → 로그인
2. 프로젝트 생성 (이름: `agent-forge` 등)
3. **API 및 서비스 → 라이브러리** → "Gmail API" 검색 → **사용** 클릭

### 2. OAuth 동의 화면

1. **API 및 서비스 → OAuth 동의 화면**
2. User Type: **외부** → 만들기
3. 앱 이름: `agent-forge`, 이메일 입력 → 저장 후 계속
4. 범위 추가: `https://www.googleapis.com/auth/gmail.readonly` → 저장
5. 테스트 사용자: 본인 Gmail 주소 추가 → 저장

### 3. OAuth 클라이언트 ID 생성

1. **API 및 서비스 → 사용자 인증 정보**
2. **+ 사용자 인증 정보 만들기 → OAuth 클라이언트 ID**
3. 유형: **웹 애플리케이션**
4. 승인된 리디렉션 URI 추가:
   ```
   http://localhost:8919/callback/gmail
   ```
5. 만들기 → **Client ID**와 **Client Secret** 복사

### 4. 환경변수 설정

```bash
cp .env.sample .env
# .env 파일에 GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET 입력
```

### 5. Setup UI 실행

```bash
make setup
```

브라우저가 자동으로 `http://localhost:8919`를 엽니다.
Gmail "연결하기" 클릭 → Google 로그인 → 동의 → 완료.

토큰은 `~/.agent-forge/tokens/`에 암호화 저장됩니다.

> **테스트 모드 주의**: 토큰이 7일마다 만료됩니다. 만료 시 `make setup`으로 "재연결"을 클릭하세요.

## 초기 설정: GitHub 연동

### Personal Access Token (간편)

```bash
# .env 파일에 추가
echo 'GITHUB_TOKEN=ghp_your-token-here' >> .env
```

GitHub → Settings → Developer settings → Personal access tokens → 생성 (repo, read:org 권한)

### OAuth (선택)

```bash
echo 'GITHUB_CLIENT_ID=your-id' >> .env
echo 'GITHUB_CLIENT_SECRET=your-secret' >> .env
```

`make setup`에서 GitHub "연결하기"로 OAuth 인증.

## MCP 서버 실행

```bash
make server       # 기본 실행 (INFO 레벨)
make debug        # DEBUG 레벨 (API 요청까지 로그)
```

Claude Code의 `.mcp.json`에서 자동으로 연결됩니다:

```json
{
  "mcpServers": {
    "workspace-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "shared.server"],
      "cwd": "tools/workspace-mcp"
    }
  }
}
```

## 로깅

`.env`에서 로그 레벨을 설정한다:

```bash
LOG_LEVEL=INFO    # 기본값 (도구 호출, 배치 사이클)
LOG_LEVEL=DEBUG   # API 요청/응답까지 모두 기록
LOG_LEVEL=WARNING # 경고와 에러만
```

로그 파일: `logs/workspace-mcp.log` (5MB 로테이션, 3개 백업)

```bash
make log          # 실시간 로그 (tail -f)
make log-all      # 전체 로그 출력
```

## MCP 도구 목록

### Gmail (5개)

| 도구 | 설명 |
|------|------|
| `gmail_list_messages` | 최근 이메일 목록 조회 |
| `gmail_read_message` | 특정 이메일 읽기 |
| `gmail_search` | Gmail 검색 쿼리로 검색 |
| `gmail_process_inbox` | 받은편지함 스캔 → Jira 티켓 감지 + 분류 + 액션 요약 |
| `gmail_read_and_analyze` | 특정 이메일 읽기 + Jira 분석 |

### GitHub (7개)

| 도구 | 설명 |
|------|------|
| `github_list_issues` | 이슈 목록 조회 |
| `github_get_issue` | 이슈 상세 조회 |
| `github_list_prs` | PR 목록 조회 |
| `github_get_pr` | PR 상세 조회 (변경 파일 포함) |
| `github_get_ci_status` | CI 상태 확인 |
| `github_setup_pr_review` | PR 리뷰 환경 셋업 (clone + checkout) |
| `github_setup_ci_debug` | CI 디버그 환경 셋업 (clone + 로그) |

### Review (9개)

| 도구 | 설명 |
|------|------|
| `review_list_pending` | 대기 중인 코드 리뷰 요청 목록 |
| `review_list_done` | 완료된 리뷰 목록 |
| `review_list_todo` | agent 작업 문서 목록 |
| `review_read_todo` | todo 문서 내용 읽기 |
| `review_create_todo` | pending → agent용 todo 문서 생성 |
| `review_update_todo` | todo 문서에 리뷰 결과 추가 |
| `review_mark_done` | 리뷰 완료 처리 (pending → done) |
| `review_get_next_action` | 다음 대기 작업 조회 (에이전트 폴링용) |
| `review_acknowledge_action` | 작업 수령 확인 (트리거 → processed 이동) |

### Task (3개)

| 도구 | 설명 |
|------|------|
| `task_list` | 태스크 목록 조회 (소스/상태 필터) |
| `task_sync` | 외부 소스에서 태스크 동기화 |
| `task_update` | 태스크 상태 업데이트 |

## 코드 리뷰 자동화

### 아키텍처

```
Gmail ──(배치 10분)──> review detector ──> data/reviews/pending/*.md
                                          + data/reviews/todo/newjob-*.md
                                          + data/triggers/pending/*.json
                                          ↓
                       외부 에이전트 ←── review_get_next_action (폴링)
                                          ↓ (clone → checkout → 분석)
                       review_mark_done → done/ 이동 + trigger processed
```

### 이벤트 시스템

배치 프로세스와 외부 에이전트 간 통신은 이벤트 + 트리거 파일 패턴으로 동작한다:

| 이벤트 | 발생 시점 | 트리거 파일 |
|--------|-----------|-------------|
| `ReviewDetected` | 새 리뷰 요청 감지 | `data/triggers/pending/review-{slug}.json` |
| `ReviewCompleted` | 리뷰 완료 처리 | `data/triggers/processed/review-{slug}.json` |
| `BatchCycleFinished` | 배치 스캔 완료 (신규 있을 때) | `data/triggers/pending/batch-{name}-{date}.json` |

외부 에이전트는 `review_get_next_action`으로 폴링하고, `review_acknowledge_action`으로 작업 수령을 확인한다.

### 사용법

```bash
# 1. 신규 리뷰 확인
/check-reviews

# 2. 리뷰 실행 (sub-agent가 clone → checkout → 분석)
/do-review

# 3. 특정 리뷰만 실행
/do-review newjob-owner-repo-42-20260317.md
```

### 파일 구조

```
data/
  reviews/
    pending/   owner-repo-42-20260317.md        ← 배치가 생성
    todo/      newjob-owner-repo-42-20260317.md  ← 배치가 자동 생성
    done/      owner-repo-42-20260317.md         ← 완료 시 이동
  triggers/
    pending/   review-owner-repo-42.json         ← 이벤트 hook이 생성
    processed/ review-owner-repo-42.json         ← acknowledge 후 이동
```

### 배치 설정

Setup UI (`http://localhost:8919`)에서 watcher 활성화/비활성화, 스캔 주기(1~60분) 설정 가능.
설정은 `~/.agent-forge/batch-config.json`에 저장.

## 룰베이스 이메일 처리

`gmail_process_inbox` 호출 시 LLM 없이 룰베이스로 동작합니다:

```
이메일 수신 → Jira 감지 (sender/subject/URL 패턴)
           → 액션 분류 (assigned/comment/status_change/...)
           → 구조화된 InboxSummary 반환
```

반환 데이터 예시:
```json
{
  "total_emails": 20,
  "jira_emails": 8,
  "action_required": [
    {
      "email_id": "msg-001",
      "subject": "[JIRA] (PROJ-123) assigned to you",
      "tickets": [{"key": "PROJ-123", "project": "PROJ"}],
      "classification": {"action": "assigned", "priority_hint": "high"},
      "requires_action": true,
      "summary": "[ACTION REQUIRED] [PROJ-123] assigned: ..."
    }
  ],
  "by_project": {"PROJ": 5, "DATA": 3},
  "by_action": {"assigned": 2, "comment": 3, "status_change": 3}
}
```

## 보안

- 토큰은 Fernet 암호화로 `~/.agent-forge/tokens/`에 저장
- MCP 응답에서 토큰 패턴 자동 제거 (`sanitize()`)
- 에러 메시지도 sanitize 적용
- LLM은 인증 정보에 접근 불가

## 테스트

```bash
make test         # 전체 테스트
make test-v       # 상세 출력
```

개별 테스트:
```bash
uv run python -m pytest tests/test_sanitize.py
uv run python -m pytest tests/test_sanitize.py::TestSanitizeEdgeCases::test_token_only_string
uv run python -m pytest -k "bearer"
uv run python -m pytest -x       # 첫 실패에서 중단
uv run python -m pytest --lf     # 실패 테스트만 재실행
```

> **참고**: `uv run`은 `.venv` 가상환경 안에서 실행합니다. `python -m pytest`로 호출해야 `src/` 경로가 Python path에 잡힙니다.

## 디렉토리 구조

```
src/
  shared/
    server.py          MCP 서버 코어
    types.py           공유 타입 정의
    sanitize.py        토큰 제거
    logging.py         로깅 설정 (파일 로테이션 + 컬러 콘솔)
    events.py          이벤트 디스패처 (ReviewDetected 등)
    hooks.py           트리거 파일 hook (에이전트 통신)
    auth/
      setup.py         OAuth 설정 웹 UI
      oauth_flow.py    OAuth 2.0 플로우
      token_store.py   암호화 토큰 저장
      credentials.py   환경변수 로딩
    batch/
      scheduler.py     배치 스케줄러 (async 백그라운드)
      config.py        배치 설정 (JSON)
    task/
      manager.py       태스크 CRUD
      store.py         파일 기반 저장
      models.py        태스크 모델
  gmail/
    client.py          Gmail REST API 래퍼
    tools.py           MCP 도구 등록 (5개)
    rules/
      jira_detector.py Jira 티켓 감지 (패턴 매칭)
      classifier.py    이메일 액션 분류
      processor.py     감지 + 분류 통합 프로세서
  github/
    client.py          GitHub REST API 래퍼
    tools.py           MCP 도구 등록 (7개)
    actions/           환경 셋업 (PR 리뷰, CI 디버그)
    monitors/          태스크 동기화 (이슈, PR, CI)
    review/
      detector.py      GitHub 리뷰 요청 이메일 감지
      models.py        ReviewRequest 모델 + 마크다운 생성
      store.py         파일 저장소 (pending/done/todo)
      watcher.py       배치 프로세서 (Gmail 스캔 → PR 수집)
      tools.py         MCP 도구 등록 (9개)
data/
  reviews/
    pending/           신규 리뷰 요청
    done/              완료된 리뷰
    todo/              agent 작업 문서
  triggers/
    pending/           대기 중인 에이전트 트리거
    processed/         처리 완료된 트리거
logs/
  workspace-mcp.log   서버 로그 (5MB 로테이션)
```
