# workspace-mcp

Gmail + GitHub MCP 서버. 이메일에서 Jira 티켓을 감지하고, GitHub 이슈/PR/CI 상태를 모니터링한다.
LLM에 토큰이 노출되지 않도록 룰베이스로 동작하며, 결과만 구조화하여 반환한다.

## 설치

```bash
cd tools/workspace-mcp
uv sync
```

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
# .env 파일 생성 (tools/workspace-mcp/ 하위)
cat > .env << 'EOF'
GMAIL_CLIENT_ID=your-client-id
GMAIL_CLIENT_SECRET=your-client-secret
EOF
```

### 5. Setup UI 실행

```bash
uv run python -m shared.auth.setup
```

브라우저가 자동으로 `http://localhost:8919`를 엽니다.
Gmail "연결하기" 클릭 → Google 로그인 → 동의 → 완료.

토큰은 `~/.agent-forge/tokens/`에 암호화 저장됩니다.

> **테스트 모드 주의**: 토큰이 7일마다 만료됩니다. 만료 시 Setup UI에서 "재연결"을 클릭하세요.

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

Setup UI에서 GitHub "연결하기"로 OAuth 인증.

## MCP 서버 실행

```bash
uv run agent-forge-server
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

### Task (3개)

| 도구 | 설명 |
|------|------|
| `task_list` | 태스크 목록 조회 (소스/상태 필터) |
| `task_sync` | 외부 소스에서 태스크 동기화 |
| `task_update` | 태스크 상태 업데이트 |

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
uv run python -m pytest -q          # 전체 테스트
uv run python -m pytest -q -x       # 첫 실패에서 중단
uv run python -m pytest tests/test_gmail_rules.py -v  # 룰 엔진만
```

## 디렉토리 구조

```
src/
  shared/
    server.py          MCP 서버 코어
    types.py           공유 타입 정의
    sanitize.py        토큰 제거
    auth/
      setup.py         OAuth 설정 웹 UI
      oauth_flow.py    OAuth 2.0 플로우
      token_store.py   암호화 토큰 저장
      credentials.py   환경변수 로딩
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
```
