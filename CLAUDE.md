# Agent Forge

Claude Code 작업을 자동화하는 방법론 프레임워크 + AI 세션 관리 런타임.

## 프로젝트 구조

Agent Forge는 두 부분으로 구성된다:

| 구성 | 경로 | 설명 |
|------|------|------|
| **v1 (방법론)** | `phases/`, `dist/`, `tools/` | Claude Code 워크플로우 자동화 (스킬, 훅, MCP 도구) |
| **v2 (런타임)** | `runtime/` | AI CLI 세션을 격리된 환경에서 관리하는 Go 바이너리 |

```
agent-forge/
  phases/                    방법론 문서 (Phase 1-4)
  dist/                      설치용 배포물 (skills, hooks)
  tools/                     MCP 서버 (Python)
    workspace-mcp/           워크스페이스 관리
    token-monitor-mcp/       토큰 사용량 모니터링

  runtime/                   Go 모듈 — forge CLI + TUI
    cmd/forge/               CLI 진입점
    internal/
      session/               세션 관리 + 상태 머신
      sandbox/               보안 정책 + settings.json 생성
      terminal/              tmux 기반 터미널 관리
      monitor/               CPU/Mem/Token 메트릭 수집
      event/                 EventBus (channel pub/sub)
      daemon/                백그라운드 데몬
      config/                설정 (~/.forge/)
      ui/                    BubbleTea TUI
    pkg/api/                 공개 API (향후 확장)

  docs/
    PHASE1-CORE-ENGINE.md    런타임 설계 스펙
    VISION-v2.md             전체 비전 (5-Layer 아키텍처)
    ARCHITECTURE.md          v1 아키텍처
    ROADMAP.md               Phase 1-4 로드맵
```

---

## v1: 방법론 프레임워크

### 워크플로우

1. **작업 시작** → `/complexity`로 Tier 판정
2. **코딩** → 작업 수행
3. **완료** → `/milestone`로 일괄 처리 (QR → delta-log → handoff → 커밋)

### Tier 분기

| Tier | 파일 수 | 절차 |
|------|---------|------|
| Micro | 1-2 | 직접 실행 → 커밋 |
| Standard | 3-10 | 계획 → 실행 → QR 1회 → handoff → 커밋 |
| Full | 10+ | 마일스톤 분해 → 마일스톤별 (실행 → QR) → handoff → 커밋 |

### 스킬 명령

| 명령 | 용도 |
|------|------|
| `/complexity` | 복잡도 평가 + Tier 추천 |
| `/qr-gate` | Quality Review (자동 수정 루프, 최대 2회) |
| `/delta-log` | delta-log 엔트리 + rolling-summary 생성 |
| `/milestone` | 완료 워크플로우 일괄 실행 |
| `/handoff` | 세션 인수인계 문서 생성 |

### 설치

```bash
# 대상 프로젝트에 코어 스킬 설치
./dist/install.sh /path/to/target-project

# 전역 설치
./dist/install.sh /path/to/target-project --global

# 리뷰 스킬 포함
./dist/install.sh /path/to/target-project --full
```

---

## v2: 런타임 (forge CLI)

Claude Code를 격리된 tmux 세션에서 실행하고, 샌드박스 정책으로 도구 접근을 제어하며, TUI로 관리한다.

### 필수 의존성

- Go 1.24+
- tmux 3.0+
- claude CLI 2.0+

### 빌드

```bash
cd runtime
go build -o forge ./cmd/forge
```

### CLI 명령

```bash
forge                          # TUI 실행 (기본)
forge new <title>              # 세션 생성
  --task "작업 설명"
  --policy restricted          # readonly/restricted/standard/full
  --project /path/to/project
  --budget 50000               # 토큰 예산
forge start <id|title>         # 세션 시작 (tmux 연동)
forge list                     # 세션 목록
forge status [id|title]        # 상태 + 메트릭
forge attach <id|title>        # 인터랙티브 연결
forge pause <id|title>         # 일시정지
forge resume <id|title>        # 재개
forge kill <id|title>          # 종료
forge log <id|title>           # 출력 표시
forge daemon start|stop|status # 백그라운드 데몬
forge config                   # 설정 표시
forge version                  # 버전
```

### 보안 정책 프리셋

| 프리셋 | 허용 도구 | 용도 |
|--------|----------|------|
| `readonly` | Read, Glob, Grep | 읽기 전용 분석 |
| `restricted` | + Write, Edit | 제한된 쓰기, 쉘 차단 |
| `standard` | + Bash(npm test, go test 등) | 일반 개발 |
| `full` | 모든 도구 | 신뢰된 작업 |

### 세션 상태 머신

```
Creating → Running ⇄ Waiting
              ↓           ↓
           Paused ←────────┘
              ↑
           Running → Completed
           Running → Failed
```

### 데이터 디렉토리

```
~/.forge/
  config.json        설정
  state.json         세션 상태
  daemon.pid         데몬 PID
  forge.log          로그
  sessions/          세션별 샌드박스
    {session-id}/
      .claude/settings.json
      CLAUDE.md
```

### 테스트

```bash
cd runtime
go test ./...                  # 전체 테스트
go test ./internal/terminal/   # tmux 통합 테스트
go test ./internal/session/    # 세션 lifecycle 테스트
go test ./internal/monitor/    # 토큰 파서 테스트
```

---

## 개발 규칙

### 커밋

- 영어 conventional commits (feat/fix/refactor/docs/test)
- Co-Author, AI attribution 금지

### 코드 표준

- 파일 200-400줄 (최대 800), 함수 <50줄
- Immutability first — 새 객체 생성, 직접 변경 금지
- 에러 핸들링 필수
- 시크릿 하드코딩 금지

### 런타임 아키텍처 규칙

- 의존 방향: `cmd/` → `ui/` → `session/` → `sandbox/`/`terminal/`/`monitor/`
- 순환 의존 금지. `event/`와 `config/`는 횡단 관심사
- 상태 전이는 SessionManager를 통해서만 수행
- claude-squad(AGPL-3.0) 코드 재사용 금지

---

## 설계 문서

| 문서 | 내용 |
|------|------|
| `docs/PHASE1-CORE-ENGINE.md` | 런타임 상세 설계 (패키지 구조, 인터페이스, 상태 머신, 샌드박스) |
| `docs/VISION-v2.md` | 전체 비전 (5-Layer 아키텍처, 브라우저 메타포) |
| `docs/ARCHITECTURE.md` | v1 방법론 아키텍처 |
| `docs/ROADMAP.md` | Phase 1-4 로드맵 |

## MCP 서버 테스트

```bash
cd tools/workspace-mcp && uv run python -m pytest -q
cd tools/token-monitor-mcp && uv run python -m pytest -q
```
