## 수정된 파일

- src/shared/sanitize.py: 통합 토큰 삭제 모듈, 9개 패턴 단일 소스 (M6)
- src/gmail/tools.py: 핸들러 실제 GmailClient 연결, _make_handler 패턴 (M6)
- src/github/tools.py: 핸들러 실제 GitHubClient 연결, action handler 에러 처리 (M6)
- src/gmail/client.py: httpx 커넥션 풀링, StoredToken 지원 (M6)
- src/github/client.py: httpx 커넥션 풀링, follow_redirects (M6)
- src/shared/auth/oauth_flow.py: 타임아웃 300s, error 파라미터, server_close (M6)
- src/shared/server.py: 최종 에러 핸들러에 sanitize() 적용 (M6)
- src/github/actions/ci_environment.py: 공유 sanitize 모듈로 전환 (M6)
- src/github/actions/git_utils.py: 공유 sanitize 모듈로 전환 (M6)
- src/shared/types.py: SecretStr for AuthConfig, Field(default_factory) (M0)
- src/shared/auth/credentials.py: SecretStr 래핑 (M0)
- src/shared/task/store.py: 절대 경로 ~/.agent-forge/tasks/ (M0)

## 핵심 결정

- Python + Pydantic > TypeScript + Node.js: Python API 클라이언트 생태계 성숙도 (M0)
- Single MCP server > 다중 서버: 공유 인프라(task store, auth) 관리 단순화 (M0)
- Fernet AES-128-CBC 토큰 암호화: 표준 대칭 암호화, 이식성 (M0)
- File-based JSON task store > DB: Git 추적 가능, 인간 판독 가능 (M0)
- Immutable Pydantic models: model_copy(update={}) 패턴으로 변이 방지 (M0)
- Handler wrapping (_make_handler) > inline error handling: DRY, 일관된 에러 경계 (M6)
- Shared sanitize module > per-file regex: 단일 소스, 패턴 드리프트 방지 (M6)
- Server.py last-defense sanitizer: 모든 미처리 예외에 sanitize() 적용 (M6)

## 미해결 사항

- shared/sanitize.py 직접 단위 테스트 없음 (M6에서 발생)
- httpx.AsyncClient 명시적 close 누락 — 리소스 누수 가능 (M6에서 발생)
- 토큰 만료 시 mid-session refresh 미구현 (M6에서 발생)
- TokenStore, OAuthFlow, FileTaskStore 직접 단위 테스트 없음 (M0에서 발생) [장기]

## 아키텍처 변경

- src/shared/sanitize.py 신규 모듈 추가: 4개 파일의 중복 패턴 통합 (M6)
- Handler wiring 아키텍처: _create_client → _make_handler → private handler 3단 구조 (M6)
- Server.py 에러 경로에 sanitization 레이어 추가 (M6)

## 다음 단계

- test_sanitize.py 추가 (9개 토큰 패턴 커버리지)
- AsyncClient.aclose() 라이프사이클 관리
- 토큰 만료 mid-session refresh 통합
- Phase 1-4 방법론 개선점 문서화 (관찰 결과 기반)
