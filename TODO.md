# Agent Forge - TODO

## 미해결 작업 목록

### 1. sanitize.py 단위 테스트 추가
- **상태**: 완료 ✓ (24 tests, `tests/test_sanitize.py`)
- **우선순위**: 높음
- **파일**: `tools/workspace-mcp/src/shared/sanitize.py`
- **대상 테스트**: `tools/workspace-mcp/tests/test_sanitize.py` (신규)
- **내용**: 9개 토큰 패턴에 대한 직접 단위 테스트 작성
  - Google OAuth (`ya29.*`)
  - GitHub PAT classic (`ghp_*`)
  - GitHub OAuth (`gho_*`)
  - GitHub fine-grained PAT (`github_pat_*`)
  - GitHub App server (`ghs_*`)
  - GitHub refresh (`ghr_*`)
  - GitHub Actions (`gha_*`)
  - Bearer 헤더
  - Generic token 헤더
- **참고**: 현재 sanitize()는 에러 경로에서 간접적으로만 호출됨. 직접 테스트 없음

#### 배경
sanitize 모듈은 에러 메시지에서 토큰을 제거하는 **보안 최종 방어선**이다.
`server.py`의 에러 핸들러, Gmail/GitHub 툴의 에러 경로, CI 로그 출력 등
5개 파일에서 사용 중이며, 패턴 하나라도 누락되면 실제 토큰이 LLM에 노출될 수 있다.

#### 테스트 범위
| 케이스 | 설명 |
|--------|------|
| 패턴별 개별 치환 | 9개 토큰 각각이 `[REDACTED]`로 치환되는지 |
| 일반 텍스트 통과 | 토큰이 없는 문자열은 그대로 반환 |
| 복수 토큰 동시 치환 | 한 문자열에 여러 토큰 포함 시 모두 치환 |
| 엣지 케이스 | 빈 문자열, 토큰만 있는 문자열, 줄바꿈 포함 |

---

### 2. AsyncClient 라이프사이클 관리
- **상태**: 완료 ✓
- **우선순위**: 높음 (리소스 누수)
- **파일**:
  - `tools/workspace-mcp/src/gmail/client.py` — GmailClient
  - `tools/workspace-mcp/src/github/client.py` — GitHubClient
- **내용**: httpx.AsyncClient가 생성 후 명시적으로 닫히지 않음
  - `aclose()` 메서드 추가 또는 AsyncContextManager 패턴 적용
  - 서버 종료 시 클라이언트 정리 보장
- **참고**: OAuth flow의 임시 클라이언트는 context manager로 정상 처리됨

#### 배경
httpx.AsyncClient는 내부적으로 커넥션 풀을 유지한다.
`aclose()`를 호출하지 않으면 TCP 연결이 열린 채로 남아 OS 파일 디스크립터가 고갈될 수 있다.
MCP 서버처럼 장시간 실행되는 프로세스에서 특히 위험하다.

**현재 문제 코드**:
```
GmailClient.__init__()  → self._http = httpx.AsyncClient(...)  # 생성만 함
GitHubClient.__init__() → self._http = httpx.AsyncClient(...)  # aclose() 없음
```

**정상 처리 사례** (같은 프로젝트 내):
```
OAuthFlow._exchange_code()  → async with httpx.AsyncClient() as client:  # 자동 정리 ✓
```

#### 해결 접근법 비교
| 접근법 | 설명 | 장점 | 단점 |
|--------|------|------|------|
| A. `aclose()` 메서드 추가 | 클라이언트에 명시적 정리 메서드 추가, 서버 shutdown에서 호출 | 기존 코드 변경 최소 | 호출 책임이 서버에 있음 |
| B. AsyncContextManager | `__aenter__`/`__aexit__` 구현, `async with`로 사용 | 자동 정리 보장 | 클라이언트 생성 코드 전체 변경 |

#### 수정 필요 파일
- `gmail/client.py`, `github/client.py` — `aclose()` 추가
- `shared/server.py` — 서버 종료 시 클라이언트 정리 hook 등록

---

### 3. 토큰 만료 mid-session refresh 통합
- **상태**: 미완
- **우선순위**: 중간
- **파일**:
  - `tools/workspace-mcp/src/shared/auth/oauth_flow.py` — refresh 로직 존재
  - `tools/workspace-mcp/src/gmail/client.py` — refresh 미연결
  - `tools/workspace-mcp/src/github/client.py` — refresh 미연결
- **내용**: OAuthFlow에 refresh 로직이 있지만 API 클라이언트에서 호출하지 않음
  - 401 응답 시 자동 refresh → 재시도 인터셉터 필요
  - 또는 요청 전 토큰 유효성 사전 검증
- **참고**: 현재는 클라이언트 생성 시점의 토큰이 만료되면 세션 내 복구 불가

#### 배경
OAuth 토큰은 보통 1시간 만료이다. MCP 서버가 한 세션에서 1시간 이상 실행되면,
처음 받은 토큰이 만료되어 모든 API 호출이 401로 실패한다.

**이미 구현된 것** (OAuthFlow):
- `get_valid_token()` — 만료 체크 + refresh_token 교환
- `_is_expired()` — 5분 버퍼로 사전 만료 감지
- `_refresh_token()` — refresh_token → 새 access_token 교환, TokenStore에 저장

**연결되지 않은 것** (API 클라이언트):
- `GmailClient.__init__(token)` — 토큰을 한 번 받고 고정
- `GitHubClient.__init__(token)` — 토큰을 한 번 받고 고정
- 만료 시 복구 경로 없음

#### 해결 접근법 비교
| 접근법 | 설명 | 장점 | 단점 |
|--------|------|------|------|
| A. 요청 전 사전 검증 | 매 API 호출 전 `get_valid_token()` 호출 → 만료 시 refresh 후 헤더 갱신 | 실패 요청 없음, 구현 단순 | 매 요청마다 만료 체크 오버헤드 |
| B. 401 응답 인터셉터 | 401 받으면 refresh → 동일 요청 재시도 | 정상 경로 오버헤드 없음 | 실패 요청 1회 발생, 재시도 로직 복잡 |

**권장**: 접근법 A. 클라이언트가 `OAuthFlow` 인스턴스를 참조하고, 매 요청 전 토큰 유효성을 검증하는 방식이 단순하다.

---

### 4. 인프라 모듈 단위 테스트
- **상태**: 미완 (장기)
- **우선순위**: 낮음
- **대상 모듈**:
  - `TokenStore` (`src/shared/auth/token_store.py`) — 암호화/복호화, 저장/로드
  - `OAuthFlow` (`src/shared/auth/oauth_flow.py`) — 토큰 발급, 갱신, 만료 검사
  - `FileTaskStore` (`src/shared/task/store.py`) — CRUD, 파일 I/O
- **참고**: conftest.py에 fixture는 존재하나 직접 단위 테스트 없음

#### 배경
이 3개 모듈은 인증과 상태 저장이라는 **기반 인프라**이다.
상위 모듈(클라이언트, 툴)은 테스트가 있지만, 기반이 깨지면 전체가 무너진다.
conftest.py에 `token_store`, `task_store` fixture가 이미 있어 테스트 환경은 갖춰져 있다.

장기 과제로 분류한 이유: 상위 레벨 통합 테스트에서 간접 검증되고 있어
즉각적인 버그 위험은 낮다. 리팩토링이나 기능 추가 시 회귀 방지를 위해 필요하다.

#### 모듈별 테스트 범위

**TokenStore** (`src/shared/auth/token_store.py`):
| 케이스 | 설명 |
|--------|------|
| 암호화 라운드트립 | 저장 → 로드 시 원본 토큰과 일치 |
| 존재하지 않는 토큰 로드 | None 반환 |
| 키 자동 생성 | `AGENT_FORGE_KEY` 없을 때 키 생성 |
| 토큰 덮어쓰기 | 동일 서비스명으로 재저장 시 업데이트 |
| 파일 권한 | 토큰 파일이 600 권한인지 (보안) |

**OAuthFlow** (`src/shared/auth/oauth_flow.py`):
| 케이스 | 설명 |
|--------|------|
| 유효 토큰 반환 | 만료 전 토큰은 그대로 반환 |
| 만료 토큰 refresh | 만료 시 `_refresh_token()` 호출 확인 |
| 만료 경계값 | 5분 버퍼 직전/직후 동작 |
| refresh 실패 | API 에러 시 적절한 예외 발생 |
| 갱신 토큰 저장 | refresh 후 TokenStore에 새 토큰 저장 |

**FileTaskStore** (`src/shared/task/store.py`):
| 케이스 | 설명 |
|--------|------|
| CRUD | 생성, 조회, 수정, 삭제 정상 동작 |
| 존재하지 않는 태스크 | 조회 시 None 또는 예외 처리 |
| JSON 라운드트립 | 직렬화 → 역직렬화 데이터 일치 |
| 빈 스토어 | 태스크 없을 때 빈 리스트 반환 |

---

## 완료된 작업 (최근)

- [x] Jira 이메일 규칙 기반 감지 및 분류 (`2423c17`)
- [x] OAuth Auth Setup 웹 UI (`4ccabae`)
- [x] state 경로 .agent-forge-state/ 이동 (`34d83ad`)
- [x] 프로젝트 로컬 state 경로 적용 (`d39c902`)
- [x] 배포 패키지 dist/ 구성 (`dad9866`)
- [x] Handler wiring 아키텍처 (M6) (`6951bb8`)
- [x] 공유 sanitize 모듈 통합 (M6)

---

## 미커밋 파일

- `CLAUDE.md` — 프로젝트 루트 (untracked, 커밋 필요 여부 결정)
