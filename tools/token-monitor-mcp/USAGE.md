# token-monitor-mcp 사용 가이드

## 개요

token-monitor Go 바이너리를 MCP 프로토콜로 래핑하여, LLM 에이전트가 세션 중 토큰 사용량을 자체 모니터링할 수 있게 한다.

## 바이너리 관리

### 설치

```bash
# token-monitor 프로젝트에서 빌드
cd /path/to/token-monitor/token-monitor
go build -ldflags "-s -w -X main.version=v0.2.0" -o dist/token-monitor ./cmd/token-monitor/

# MCP 프로젝트의 bin/ 디렉토리에 복사
cp dist/token-monitor /path/to/agent-forge/tools/token-monitor-mcp/bin/
```

### 버전 확인

```bash
tools/token-monitor-mcp/bin/token-monitor help
# token-monitor v0.2.0
```

`bin/VERSION` 파일에 현재 바이너리 버전이 기록되어 있다.

### 업데이트

1. token-monitor 프로젝트에서 새 버전 빌드
2. `bin/token-monitor` 교체
3. `bin/VERSION` 갱신
4. MCP 테스트 실행으로 호환성 확인

## MCP 도구 목록

| 도구 | 용도 | 호출 시점 |
|------|------|----------|
| `token_session_list` | 세션 목록 조회 | 세션 시작 시 현재 세션 확인 |
| `token_session_summary` | 세션 토큰 현황 (총/입력/출력/캐시/비용) | 마일스톤 완료 시 1회 |
| `token_cost_check` | 현재 비용 빠른 확인 | 비용 의식적 판단 필요 시 |
| `token_session_export` | agent-forge 포맷 내보내기 | 세션 종료 시 session-log 자동 생성 |
| `token_monitor_version` | 바이너리 버전 확인 | 디버깅 시 |

## 에이전트 활용 패턴

### 마일스톤 완료 시 자동 기록

```
1. 코드 작업 완료
2. QR 게이트 실행
3. token_session_summary 호출 → 현재 토큰 현황 확인
4. delta-log에 토큰 정보 포함하여 기록
5. 커밋
```

### 비용 임계값 기반 전략 변경

```
1. token_cost_check 호출
2. 비용이 높으면 → 접근 방식 단순화 검토
3. 비용이 낮으면 → 추가 검증/테스트 여유
```

### 세션 종료 시 session-log 자동 생성

```
1. token_session_export (format: agent-forge) 호출
2. 출력의 tokens 블록을 Phase 4 session-log에 매핑
3. duration_minutes는 자동 계산됨
```

## 출력 포맷

### token_session_summary 응답

```json
{
  "success": true,
  "data": {
    "session_id": "abc-123",
    "project": "agent-forge",
    "date": "2026-03-12",
    "tokens": {
      "total": 50000,
      "input": 30000,
      "output": 20000,
      "cache_read": 5000,
      "cache_create": 2000
    },
    "cost_usd": 0.45,
    "duration_minutes": 60
  }
}
```

### token_session_export (agent-forge 포맷) 응답

```json
{
  "success": true,
  "data": {
    "session_id": "abc-123",
    "date": "2026-03-12",
    "project": "agent-forge",
    "tokens": {
      "total": 50000,
      "input": 30000,
      "output": 20000,
      "cache_read": 5000,
      "cache_create": 2000,
      "cost_usd": 0.45
    },
    "duration_minutes": 60
  }
}
```

## Phase 4 session-log 필드 매핑

| MCP 응답 필드 | session-log 필드 |
|--------------|-----------------|
| `data.tokens.total` | `tokens.total` |
| `data.tokens.input` | `tokens.input` |
| `data.tokens.output` | `tokens.output` |
| `data.tokens.cache_read` | `tokens.cache_read` |
| `data.tokens.cache_create` | `tokens.cache_create` |
| `data.cost_usd` | `tokens.cost_usd` |
| `data.duration_minutes` | `duration_minutes` |
