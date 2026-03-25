# agent-forge

## agent-forge Methodology

이 프로젝트는 agent-forge 방법론을 적용하여 Claude Code 작업을 자동화한다.

### 워크플로우

1. **작업 시작** → `/complexity`로 Tier 판정 (Full시 마일스톤 자동 분해)
2. **코딩** → 작업 수행
3. **완료** → `/milestone`로 일괄 처리 (QR → delta-log → handoff → 토큰 → 커밋)

### Tier 분기

| Tier | 파일 수 | 절차 |
|------|---------|------|
| Micro | 1-2 | 직접 실행 → 커밋 |
| Standard | 3-10 | 계획 → 실행 → QR 1회 → handoff → 커밋 |
| Full | 10+ | 마일스톤 분해 → 마일스톤별 (실행 → QR) → handoff → 커밋 |

### 사용 가능한 명령

| 명령 | 용도 |
|------|------|
| `/complexity` | 복잡도 평가, Tier 추천, Full시 마일스톤 자동 분해 |
| `/qr-gate` | Quality Review (자동 수정 루프 포함, 최대 2회) |
| `/delta-log` | delta-log 엔트리 + rolling-summary 생성 |
| `/milestone` | 전체 완료 워크플로우 일괄 실행 (handoff 포함) |
| `/handoff` | 세션 인수인계 문서 생성 |

### 커밋 규칙

- 영어 conventional commits (feat/fix/refactor/docs/test)
- Co-Author, AI attribution 금지

### 코드 표준

- 파일 200-400줄 (최대 800), 함수 <50줄
- Immutability first
- 에러 핸들링 필수
- 시크릿 하드코딩 금지

---

## Project Overview

Claude Code에서 사용하는 에이전트 개발 방법론 프레임워크 + MCP 도구 플랫폼.
다른 프로젝트에 설치하여 토큰 절약, 품질 검증, 작업 기록을 자동화한다.

## Architecture

```
agent-forge/
  phases/                    방법론 문서 (Phase 1-4)
    phase-1-process-model/   워크플로우 Tier, QR 규칙
    phase-2-domain-profiles/ 도메인 프로필 스키마, 통합 가이드
    phase-3-context-management/ 델타 로그, 롤링 요약
    phase-4-measurement/     수집 가이드, 분석 플레이북
  tools/
    workspace-mcp/           Gmail + GitHub MCP 서버 (Python)
    token-monitor-mcp/       토큰 모니터링 MCP 서버 (Python → Go binary)
  dist/                      대상 프로젝트 설치용 배포물
    install.sh               설치 스크립트
    skills/                  /complexity, /qr-gate, /delta-log, /milestone, /handoff, /check-reviews, /do-review
    hooks/                   pre-commit QR, session-end checklist
    templates/               CLAUDE.md 템플릿
  delta-logs/                프로젝트 레벨 마일스톤 기록
```

## Development Commands

```bash
# workspace-mcp 테스트
cd tools/workspace-mcp && uv run python -m pytest -q

# token-monitor-mcp 테스트
cd tools/token-monitor-mcp && uv run python -m pytest -q

# 대상 프로젝트에 설치 (core skills)
./dist/install.sh /path/to/target-project

# 전역 설치 (모든 프로젝트에 skills 적용)
./dist/install.sh /path/to/target-project --global

# 리뷰 스킬 포함 설치
./dist/install.sh /path/to/target-project --full
```
