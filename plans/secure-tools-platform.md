# Plan: Secure Tools Platform

## 목적

LLM에 인증 토큰을 전달하지 않으면서, 외부 서비스(Gmail, GitHub 등)의 정보를 LLM이 활용할 수 있도록 하는 MCP 기반 도구 플랫폼.

## 핵심 설계 결정

### D1: 토큰 격리 아키텍처

LLM은 토큰을 절대 보지 않는다. 도구 서버가 토큰을 보유하고, LLM에게는 결과 데이터만 전달.

```
┌──────────┐     MCP (데이터만)     ┌──────────────┐
│  Claude   │◄────────────────────►│  Tool Server  │
│  (LLM)   │  토큰 없음, 결과만    │  (토큰 보유)   │
└──────────┘                      └──────┬───────┘
                                        │ OAuth / API Key
                                        ▼
                              ┌──────────────────┐
                              │  External APIs    │
                              │  Gmail, GitHub    │
                              └──────────────────┘
```

### D2: 기술 스택

| 선택 | 이유 |
|------|------|
| Python 3.12+ | Google/GitHub API 클라이언트 생태계가 가장 성숙 |
| FastAPI | 비동기 지원, OAuth 미들웨어, Pydantic 통합 |
| Pydantic v2 | 태스크 스키마 런타임 검증, JSON Schema 자동 생성 |
| MCP Python SDK (`mcp`) | 공식 지원, TypeScript SDK와 동등 수준 |
| OAuth 2.0 (authlib) | Google/GitHub 표준 인증 |
| JSON | 태스크 관리 파일 형식 (Pydantic 모델과 직접 호환) |

### D3: 확장 가능한 폴더 구조

새로운 도구(Slack, Jira, etc.)를 추가할 때 기존 코드를 수정하지 않고 새 패키지만 추가.

```
tools/
├── pyproject.toml              프로젝트 설정 (dependencies, scripts)
├── src/                        소스 패키지 (src-layout)
│   ├── shared/                 공유 인프라
│   │   ├── __init__.py
│   │   ├── server.py           MCP 서버 코어
│   │   ├── types.py            공유 타입 (Pydantic)
│   │   ├── auth/               인증 관리
│   │   │   ├── __init__.py
│   │   │   ├── token_store.py  토큰 암호화 저장 (Fernet)
│   │   │   ├── oauth_flow.py   OAuth 2.0 플로우
│   │   │   └── credentials.py  자격증명 관리
│   │   └── task/               태스크 관리
│   │       ├── __init__.py
│   │       ├── manager.py      태스크 CRUD
│   │       ├── models.py       Pydantic 모델 (스키마 겸용)
│   │       └── store.py        파일 기반 저장
│   │
│   ├── gmail/                  Gmail 도구
│   │   ├── __init__.py
│   │   ├── tools.py            MCP 도구 등록
│   │   ├── client.py           Gmail API 클라이언트
│   │   └── monitor.py          이메일 모니터링
│   │
│   ├── github/                 GitHub 도구
│   │   ├── __init__.py
│   │   ├── tools.py            MCP 도구 등록
│   │   ├── client.py           GitHub API 클라이언트
│   │   ├── monitors/           모니터링 모듈
│   │   │   ├── __init__.py
│   │   │   ├── issue_monitor.py
│   │   │   ├── pr_monitor.py
│   │   │   └── ci_monitor.py
│   │   └── actions/            실행 모듈
│   │       ├── __init__.py
│   │       ├── pr_environment.py
│   │       └── ci_environment.py
│   │
│   └── _template/              새 도구 템플릿
│       ├── __init__.py
│       ├── tools.py
│       └── client.py
```

### D4: 태스크 관리 스키마

Pydantic 모델로 정의하여 런타임 검증과 JSON Schema 자동 생성을 동시에 달성.

```python
class Task(BaseModel):
    id: str
    type: Literal["issue", "pr", "ci_failure", "email"]
    status: Literal["open", "in_progress", "resolved", "closed"]
    priority: Literal["critical", "high", "medium", "low"]
    title: str
    source: str
    source_url: str
    source_id: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = {}

class TaskStore(BaseModel):
    version: str = "1.0"
    source: str
    tasks: list[Task] = []
```

### D5: MCP 도구 설계

LLM이 호출할 수 있는 MCP 도구 목록:

**Gmail 도구**:
| 도구 | 설명 | 입력 | 출력 |
|------|------|------|------|
| `gmail_list_messages` | 이메일 목록 조회 | query, max_results | 메일 목록 (제목, 발신자, 날짜) |
| `gmail_read_message` | 이메일 본문 읽기 | message_id | 본문 텍스트 |
| `gmail_search` | 이메일 검색 | query | 검색 결과 |

**GitHub 도구**:
| 도구 | 설명 | 입력 | 출력 |
|------|------|------|------|
| `github_list_issues` | 이슈 목록 | repo, state, labels | 이슈 목록 |
| `github_get_issue` | 이슈 상세 | repo, issue_number | 이슈 내용 |
| `github_list_prs` | PR 목록 | repo, state | PR 목록 |
| `github_get_pr` | PR 상세 + diff | repo, pr_number | PR 내용, 변경 파일 |
| `github_get_ci_status` | CI 상태 | repo, ref | CI 결과, 로그 |
| `github_setup_pr_review` | PR 리뷰 환경 구성 | repo, pr_number, target_dir | clone + checkout 결과 |
| `github_setup_ci_debug` | CI 디버깅 환경 구성 | repo, run_id, target_dir | clone + 실패 로그 |

**태스크 도구**:
| 도구 | 설명 | 입력 | 출력 |
|------|------|------|------|
| `task_list` | 태스크 목록 | source, status, type | 태스크 목록 |
| `task_sync` | 소스에서 태스크 동기화 | source, repo | 동기화 결과 |
| `task_update` | 태스크 상태 변경 | task_id, status | 변경 결과 |

### D6: 보안 원칙

- 토큰은 Fernet(AES-128-CBC) 대칭 암호화로 로컬 파일에 저장
- 암호화 키는 환경 변수 또는 OS keyring에서 로드
- MCP 응답에 토큰, API 키, 인증 헤더가 절대 포함되지 않음
- Gmail은 read-only scope만 요청 (gmail.readonly)
- GitHub은 최소 권한 scope (repo:read, issues:read, pull_requests:read)
- 환경 변수로 민감 설정 관리 (python-dotenv)

### D7: 기각된 대안

| 대안 | 기각 이유 |
|------|----------|
| TypeScript + Node.js | API 클라이언트 생태계가 Python보다 덜 성숙, MCP SDK는 Python도 동등 지원 |
| YAML 태스크 파일 | JSON이 Pydantic 모델과 직접 호환, 스키마 검증 용이 |
| 각 도구를 별도 MCP 서버로 | 서버 관리 복잡도 증가, 단일 서버 + 도구 분리가 더 실용적 |
| DB 기반 태스크 저장 | 파일 기반이 git 추적 가능, LLM이 직접 읽기 가능 |
| Django/Flask | FastAPI의 비동기 지원 + Pydantic 네이티브 통합이 이 유스케이스에 최적 |

---

## 마일스톤

### M1: 프로젝트 초기화 + 공유 인프라

**산출물**:
- pyproject.toml, 의존성 설치 (uv 또는 pip)
- tools/shared/types.py — 공유 타입 정의 (Pydantic)
- tools/shared/auth/ — 토큰 저장/관리 (Fernet 암호화)
- tools/shared/task/ — 태스크 매니저 + Pydantic 모델
- tools/shared/server.py — MCP 서버 코어 (빈 도구 목록으로 시작)

**검증**: MCP 서버가 빈 도구 목록으로 시작되고, 토큰 저장/로드가 동작

### M2: Gmail 도구

**산출물**:
- tools/gmail/ — Gmail API 클라이언트 + 모니터링
- Google OAuth 2.0 플로우 (gmail.readonly scope, authlib)
- MCP 도구 3개 (list, read, search)
- 태스크 관리 연동

**검증**: `gmail_list_messages` 호출 시 이메일 목록 반환, 토큰이 MCP 응답에 없음

### M3: GitHub 도구 — 모니터링

**산출물**:
- tools/github/client.py — GitHub API 클라이언트 (PyGithub 또는 httpx)
- tools/github/monitors/ — 이슈, PR, CI 모니터링
- MCP 도구 5개 (list_issues, get_issue, list_prs, get_pr, get_ci_status)
- 태스크 자동 동기화 (이슈 → 태스크, PR → 태스크, CI 실패 → 태스크)

**검증**: `github_list_issues` 호출 시 이슈 목록 반환, 태스크 파일에 동기화됨

### M4: GitHub 도구 — 환경 구성

**산출물**:
- tools/github/actions/pr_environment.py — PR 리뷰 환경 (clone + checkout)
- tools/github/actions/ci_environment.py — CI 디버깅 환경 (clone + 실패 로그)
- MCP 도구 2개 (setup_pr_review, setup_ci_debug)

**검증**: `github_setup_pr_review` 호출 시 지정 폴더에 repo clone + PR checkout 완료

### M5: 통합 + 도구 템플릿

**산출물**:
- tools/_template/ — 새 도구 추가 템플릿
- 전체 통합 테스트 (pytest)
- MCP 서버 설정 파일 (.mcp.json)
- 사용 가이드

**검증**: 전체 도구가 단일 MCP 서버에서 동작, 새 도구 추가 시 기존 코드 수정 없음

---

## 위험

| 위험 | 영향 | 대응 |
|------|------|------|
| Google OAuth 설정 복잡도 | M2 지연 | OAuth playground로 먼저 테스트, 실패 시 App Password 대안 |
| GitHub rate limit | M3 기능 제한 | 조건부 요청 (If-None-Match), 캐싱 |
| MCP 프로토콜 변경 | 전체 영향 | mcp 패키지 버전 고정 |
| Python 의존성 충돌 | 환경 문제 | uv로 격리된 venv 관리 |
