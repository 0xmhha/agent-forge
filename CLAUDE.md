# agent-forge

MCP 기반 도구 플랫폼 + 에이전트 개발 방법론 프레임워크.

## 프로젝트 구조

```
agent-forge/
  phases/           Phase 1-4 방법론 문서
  tools/
    workspace-mcp/  Gmail + GitHub MCP 서버
    token-monitor-mcp/  토큰 모니터링 MCP 서버
  delta-logs/       마일스톤별 증분 기록 (프로젝트 레벨)
  .claude/skills/   자동화 스킬 (/milestone, /qr-gate, /delta-log, /complexity)
```

## 방법론 워크플로우 (모든 작업에 자동 적용)

### 1단계: 복잡도 평가 → Tier 선택

```
IF 파일 <= 2 AND 의존성 영향 없음 → Micro (QR 생략)
ELSE IF 파일 <= 10 AND 아키텍처 영향 경미 → Standard (QR 1회)
ELSE → Full (마일스톤별 QR)
```

### 2단계: 작업 실행

- Micro: 직접 실행 → 완료
- Standard: 간략 계획 → 실행 → QR 1회 (커밋 전) → 완료
- Full: 상세 계획 → 마일스톤별 (실행 → QR) → 문서화 → 완료

### 3단계: QR 게이트 (커밋 전 필수, Micro 제외)

심각도: MUST (차단) > SHOULD (권장) > COULD (선택)

도메인 프로필이 있으면:
- forbidden_patterns → 위반 검사
- required_patterns → 존재 검사
- priority_matrix → 심각도 가중치 조정

### 4단계: delta-log 기록

마일스톤 완료 시 `delta-logs/M{N}-{slug}.json` 생성.
필수 필드: milestone, timestamp, files_changed, decisions, qr_result

### 5단계: 토큰 기록

token-monitor-mcp의 `token_session_export` (agent-forge 포맷) 호출하여 session-log 자동 생성.

## 커밋 규칙

- 영어 conventional commits (feat/fix/refactor/docs/test)
- Co-Author, AI attribution 금지
- 개발 단계 용어 금지

## 코드 표준

- 파일 200-400줄 (최대 800), 함수 <50줄
- Immutability first, composition over inheritance
- 에러 핸들링 필수, console.log 금지
- 시크릿 하드코딩 금지

## 도메인 프로필

각 MCP 프로젝트는 `domain-profile.yaml`을 가질 수 있음.
없으면 상위 디렉토리의 프로필 적용. 루트에도 없으면 기본값.

## MCP 서버

- workspace-mcp: `tools/workspace-mcp/.venv/bin/python -m shared.server`
- token-monitor-mcp: `tools/token-monitor-mcp/.venv/bin/python -m token_monitor_mcp.server`

## 스킬 (자동화 명령)

- `/milestone` — 마일스톤 완료 워크플로우 (QR → delta-log → 토큰 기록 → 커밋)
- `/qr-gate` — Quality Review 실행
- `/delta-log` — delta-log 엔트리 생성
- `/complexity` — 복잡도 평가 및 Tier 추천

## 참조 문서

- `phases/phase-1-process-model/` — 워크플로우 Tier, QR 규칙
- `phases/phase-2-domain-profiles/` — 도메인 프로필 스키마, 통합 가이드
- `phases/phase-3-context-management/` — 델타 로그, 롤링 요약
- `phases/phase-4-measurement/` — 수집 가이드, 분석 플레이북
- `tools/token-monitor-mcp/USAGE.md` — 토큰 모니터링 사용법
