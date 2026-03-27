# Phase 1: Core Engine — 상세 설계

> Agent Forge v2 Layer 2 (Agent Runtime) 구현을 위한 Core Engine 설계 문서
> 작성일: 2026-03-26

---

## 1. 목표와 범위

### 1.1 Phase 1이 달성할 것

**"Claude Code를 격리된 환경에서 백그라운드로 실행하고, 세션을 관리하며, 상태를 모니터링하는 핵심 엔진"**

구체적으로:
- 세션 생성 시 샌드박스 디렉토리를 자동 구성 (settings.json, CLAUDE.md)
- tmux 기반 터미널에서 Claude Code를 실행/관리
- 세션 상태 추적 (생성 → 실행 → 대기 → 일시정지 → 완료/실패)
- 프로세스 메트릭 수집 (CPU, 메모리, 토큰 사용량)
- TUI 또는 CLI로 세션을 제어
- 프로세스 재시작 후 세션 복원

### 1.2 Phase 1이 포함하지 않는 것

- 웹 GUI (Phase 4)
- 멀티 모델 지원 — Codex, Gemini (Phase 2)
- Tool Registry / 스코어링 (Phase 2)
- 작업 자동 분해 / Orchestrator (Phase 3)
- 그래프 메모리 (Phase 3)

### 1.3 VISION-v2 Layer 매핑

```
VISION-v2 Layer          Phase 1 구현 범위
─────────────────────    ──────────────────
Layer 1: UI Shell        → TUI (BubbleTea) + CLI commands
Layer 2: Agent Runtime   → Core Engine (이 문서의 전체 범위)
Layer 3: Tool Registry   → (미포함)
Layer 4: Orchestrator    → (미포함)
Layer 5: Agentic OS      → (미포함)
```

---

## 2. 기술 결정

### 2.1 언어: Go

| 근거 | 상세 |
|------|------|
| 프로세스 관리 | `os/exec`, PTY 라이브러리가 성숙 |
| 동시성 | goroutine + channel로 자연스러운 async 패턴 |
| 단일 바이너리 | 설치 = 파일 하나 복사, cross-compile 지원 |
| tmux 연동 | 쉘 명령 실행이 직관적 |
| 성능 | 데몬으로 장시간 실행 시 메모리 효율 |

VISION-v2의 Node.js + Hono는 **Layer 1(Web UI)**에서 사용. Core Engine(Layer 2)은 Go로 구현하고, 향후 gRPC/WebSocket으로 Web UI와 연결.

### 2.2 핵심 의존성

| 패키지 | 용도 | 선택 이유 |
|--------|------|----------|
| `charmbracelet/bubbletea` | TUI 프레임워크 | Go TUI 표준, 이벤트 기반 |
| `charmbracelet/lipgloss` | TUI 스타일링 | BubbleTea 공식 스타일링 |
| `creack/pty` | PTY 생성/관리 | Go PTY 표준 라이브러리 |
| `shirou/gopsutil` | 프로세스 메트릭 | CPU/Mem/Net 크로스플랫폼 |
| `spf13/cobra` | CLI 프레임워크 | Go CLI 표준 |
| `google/uuid` | 세션 ID 생성 | RFC 4122 UUID |

### 2.3 기각한 대안

| 대안 | 기각 이유 |
|------|----------|
| Node.js (전체) | PTY/프로세스 관리에서 Go보다 불안정, GC 지연 |
| Rust | 학습 곡선, BubbleTea급 TUI 생태계 부재 |
| Python | 성능, 타입 안정성, 배포 복잡도 |
| Docker 기반 격리 | Phase 1 MVP에는 과도, 설정 기반 격리로 충분 |
| 직접 PTY (tmux 없음) | 세션 지속성(detach/reattach) 구현 비용 높음 |

---

## 3. 프로젝트 구조

### 3.1 디렉토리 레이아웃

```
agent-forge/
├── (기존 v1 구조 유지)
│   ├── phases/
│   ├── tools/
│   ├── dist/
│   └── docs/
│
└── runtime/                      # NEW: Go 모듈 (Core Engine)
    ├── go.mod                    # module github.com/{user}/agent-forge/runtime
    ├── go.sum
    │
    ├── cmd/
    │   └── forge/
    │       └── main.go           # CLI 진입점
    │
    ├── internal/                 # 비공개 패키지 (구현 상세)
    │   ├── session/              # 세션 관리
    │   │   ├── session.go        # Session 구조체 + 비즈니스 로직
    │   │   ├── state.go          # 상태 머신 (전이 규칙)
    │   │   ├── manager.go        # SessionManager (CRUD + lifecycle)
    │   │   └── store.go          # 영속화 (JSON 직렬화)
    │   │
    │   ├── sandbox/              # 샌드박스 구성
    │   │   ├── sandbox.go        # Sandbox 생성/정리
    │   │   ├── policy.go         # 보안 정책 (allow/deny 규칙)
    │   │   ├── preset.go         # 사전 정의 정책 프리셋
    │   │   └── generator.go      # settings.json + CLAUDE.md 생성기
    │   │
    │   ├── terminal/             # 터미널 추상화
    │   │   ├── terminal.go       # Terminal 인터페이스
    │   │   ├── tmux.go           # tmux 기반 구현
    │   │   ├── capture.go        # 출력 캡처 + 변경 감지
    │   │   └── pty.go            # PTY 유틸리티
    │   │
    │   ├── monitor/              # 리소스 모니터링
    │   │   ├── monitor.go        # Monitor 오케스트레이터
    │   │   ├── process.go        # CPU/메모리 수집
    │   │   ├── token.go          # 토큰 사용량 파싱
    │   │   └── metrics.go        # 메트릭 타입 정의
    │   │
    │   ├── daemon/               # 백그라운드 데몬
    │   │   ├── daemon.go         # 데몬 lifecycle (start/stop)
    │   │   └── worker.go         # 백그라운드 워커 (polling, auto-respond)
    │   │
    │   ├── event/                # 이벤트 시스템
    │   │   └── bus.go            # EventBus (pub/sub via channels)
    │   │
    │   ├── config/               # 설정 관리
    │   │   ├── config.go         # 앱 설정 구조체
    │   │   └── paths.go          # 파일 경로 해석
    │   │
    │   └── ui/                   # TUI 레이어
    │       ├── app.go            # BubbleTea 앱 (Model + Update + View)
    │       ├── layout.go         # 레이아웃 계산
    │       ├── session_list.go   # 세션 목록 컴포넌트
    │       ├── preview.go        # 출력 미리보기 컴포넌트
    │       ├── monitor_panel.go  # 모니터링 패널 컴포넌트
    │       ├── menu.go           # 하단 메뉴 (키 바인딩 안내)
    │       ├── overlay/          # 오버레이 (입력, 확인, 도움말)
    │       │   ├── input.go
    │       │   ├── confirm.go
    │       │   └── help.go
    │       └── keys.go           # 키 바인딩 정의
    │
    └── pkg/                      # 공개 패키지 (향후 외부 연동용)
        └── api/
            ├── types.go          # 공개 타입 (Session, Metrics 등)
            └── service.go        # 서비스 인터페이스 (gRPC/HTTP 준비)
```

### 3.2 의존성 방향 (레이어드 아키텍처)

```
cmd/forge/main.go
    │
    ├── internal/ui/          ← TUI (최상위, 사용자와 직접 소통)
    │   ├── internal/session/ ← 세션 관리
    │   │   ├── internal/sandbox/   ← 샌드박스 구성
    │   │   ├── internal/terminal/  ← 터미널 관리
    │   │   └── internal/monitor/   ← 메트릭 수집
    │   └── internal/event/   ← 이벤트 버스 (횡단 관심사)
    │
    ├── internal/daemon/      ← 데몬 (UI 없이 독립 실행 가능)
    │   └── internal/session/
    │
    └── internal/config/      ← 설정 (모든 패키지에서 사용)
```

**규칙**: 화살표 방향으로만 의존. 순환 의존 금지. `event/`와 `config/`는 횡단 관심사.

---

## 4. 핵심 타입 및 인터페이스

### 4.1 Session (세션)

```go
// internal/session/session.go

package session

type Status int

const (
    StatusCreating  Status = iota  // 샌드박스 구성 중
    StatusRunning                  // Claude Code 실행 중 (AI가 작업 수행 중)
    StatusWaiting                  // Claude Code가 사용자 입력 대기 중
    StatusPaused                   // 일시정지 (터미널 분리, 샌드박스 보존)
    StatusCompleted                // 작업 완료
    StatusFailed                   // 에러 발생
)

type SessionConfig struct {
    Title       string            // 세션 이름 (사용자 지정)
    Task        string            // AI에게 전달할 작업 설명
    ProjectPath string            // 대상 프로젝트 경로 (빈 값이면 새 프로젝트)
    PolicyName  string            // 샌드박스 정책 프리셋 이름
    UseWorktree bool              // git worktree 사용 여부
    TokenBudget int64             // 토큰 예산 (0 = 무제한)
}

type Session struct {
    // 식별
    ID          string            // UUID v4
    Title       string
    Task        string

    // 상태
    Status      Status
    ExitCode    int               // 종료 코드 (Completed/Failed 시)
    ErrorMsg    string            // 에러 메시지 (Failed 시)

    // 샌드박스
    SandboxDir  string            // 샌드박스 루트 경로
    PolicyName  string            // 적용된 정책 이름
    ProjectPath string            // 원본 프로젝트 경로

    // 타임스탬프
    CreatedAt   time.Time
    StartedAt   time.Time
    UpdatedAt   time.Time
    CompletedAt time.Time

    // 런타임 (직렬화하지 않음)
    terminal    terminal.Terminal // 터미널 연결
    metrics     Metrics           // 최신 메트릭
}

// Metrics는 세션의 리소스 사용량 스냅샷
type Metrics struct {
    CPUPercent    float64
    MemoryMB      float64
    TokensUsed    int64
    TokenBudget   int64
    NetworkActive bool
    CollectedAt   time.Time
}
```

### 4.2 SessionManager (세션 관리자)

```go
// internal/session/manager.go

type SessionManager struct {
    sessions  map[string]*Session  // ID → Session
    store     Store                // 영속화
    eventBus  event.Bus            // 이벤트 발행
    config    *config.Config
    mu        sync.RWMutex         // 동시성 보호
}

// 퍼블릭 메서드 (UI/CLI/Daemon이 호출)
type Manager interface {
    // Lifecycle
    Create(cfg SessionConfig) (*Session, error)
    Start(sessionID string) error
    Pause(sessionID string) error
    Resume(sessionID string) error
    Kill(sessionID string) error

    // Query
    Get(sessionID string) (*Session, error)
    List() []*Session
    ListByStatus(status Status) []*Session

    // I/O
    SendInput(sessionID string, input []byte) error
    CaptureOutput(sessionID string) (string, error)
    HasOutputChanged(sessionID string) bool

    // Attach/Detach (TUI에서 세션에 직접 연결)
    Attach(sessionID string, stdin io.Reader, stdout io.Writer) (<-chan struct{}, error)
    Detach(sessionID string) error

    // Metrics
    GetMetrics(sessionID string) (Metrics, error)
}
```

### 4.3 Terminal (터미널 추상화)

```go
// internal/terminal/terminal.go

// Terminal은 프로세스 실행 환경을 추상화한다.
// 구현체: TmuxTerminal (Phase 1), ContainerTerminal (향후)
type Terminal interface {
    // Lifecycle
    Start(cfg TerminalConfig) error
    Stop() error
    IsRunning() bool

    // I/O
    Write(data []byte) (int, error)
    CaptureOutput() (string, error)
    HasChanged() bool

    // Attach/Detach (인터랙티브 모드)
    Attach(stdin io.Reader, stdout io.Writer) (<-chan struct{}, error)
    Detach() error

    // Window
    Resize(cols, rows uint16) error

    // Info
    PID() (int, error)
    Name() string
}

type TerminalConfig struct {
    Name       string   // 터미널 세션 이름 (고유)
    WorkDir    string   // 작업 디렉토리
    Command    string   // 실행할 명령 (예: "claude")
    Args       []string // 명령 인자
    Env        []string // 환경 변수 (KEY=VALUE)
    Cols       uint16   // 초기 너비
    Rows       uint16   // 초기 높이
}
```

### 4.4 Sandbox (샌드박스)

```go
// internal/sandbox/sandbox.go

// Sandbox는 세션의 격리된 실행 환경을 관리한다.
type Sandbox struct {
    ID          string          // 세션 ID와 동일
    RootDir     string          // 샌드박스 루트 디렉토리
    Policy      Policy          // 적용된 보안 정책
    WorktreeDir string          // git worktree 경로 (사용 시)
}

// Setup은 샌드박스 디렉토리를 생성하고 설정 파일을 배치한다.
func Setup(cfg SandboxConfig) (*Sandbox, error)

// Teardown은 샌드박스 디렉토리를 정리한다.
func (s *Sandbox) Teardown() error

// Preserve는 일시정지 시 샌드박스를 보존한다 (worktree만 제거).
func (s *Sandbox) Preserve() error

type SandboxConfig struct {
    SessionID   string
    Policy      Policy
    ProjectPath string          // 원본 프로젝트 (빈 값이면 빈 디렉토리)
    UseWorktree bool
    TaskPrompt  string          // CLAUDE.md에 포함할 작업 설명
}
```

### 4.5 Policy (보안 정책)

```go
// internal/sandbox/policy.go

// Permission은 Claude Code의 도구 사용 권한을 정의한다.
type Permission struct {
    Tool    string  // "Bash", "Read", "Write", "Edit", "Glob", "Grep", "Agent" 등
    Pattern string  // 선택: 파일/명령 패턴 (예: "npm test", "src/**")
}

// Policy는 샌드박스의 보안 규칙 집합이다.
type Policy struct {
    Name        string
    Description string

    // Claude Code settings.json에 매핑
    Allow       []Permission    // 허용 도구 목록
    Deny        []Permission    // 차단 도구 목록

    // 추가 제약
    AllowedPaths  []string      // 접근 가능 경로 패턴 (빈 = 제한 없음)
    TokenBudget   int64         // 토큰 예산 (0 = 무제한)
    NetworkAccess bool          // 네트워크 접근 허용

    // CLAUDE.md에 주입할 추가 지시사항
    Instructions  string
}
```

### 4.6 EventBus (이벤트 시스템)

```go
// internal/event/bus.go

type Type int

const (
    SessionCreated Type = iota
    SessionStarted
    SessionStatusChanged
    SessionOutputChanged
    SessionCompleted
    SessionFailed
    MetricsUpdated
)

type Event struct {
    Type      Type
    SessionID string
    Data      any
    Timestamp time.Time
}

// Bus는 컴포넌트 간 비동기 이벤트 전달을 담당한다.
type Bus interface {
    Publish(event Event)
    Subscribe(types ...Type) <-chan Event
    Unsubscribe(ch <-chan Event)
    Close()
}
```

### 4.7 Store (영속화)

```go
// internal/session/store.go

// Store는 세션 데이터의 영속화를 담당한다.
type Store interface {
    SaveAll(sessions []*Session) error
    LoadAll() ([]*Session, error)
    Save(session *Session) error
    Delete(sessionID string) error
}

// FileStore는 JSON 파일 기반 Store 구현체
type FileStore struct {
    path string  // ~/.forge/state.json
}
```

### 4.8 Monitor (메트릭 수집)

```go
// internal/monitor/monitor.go

// Collector는 특정 종류의 메트릭을 수집한다.
type Collector interface {
    Collect(pid int, output string) (any, error)
}

// Monitor는 모든 세션의 메트릭을 주기적으로 수집한다.
type Monitor struct {
    interval    time.Duration
    collectors  []Collector
    eventBus    event.Bus
}

// ProcessCollector: CPU%, Memory (gopsutil)
// TokenCollector: Claude Code stdout에서 토큰 사용량 파싱
// NetworkCollector: 프로세스의 네트워크 활동 감지
```

---

## 5. 세션 상태 머신

### 5.1 상태 전이도

```
                 ┌──────────────┐
                 │   Creating   │
                 └──────┬───────┘
                        │ sandbox ready + claude started
                        ▼
              ┌──────────────────┐
         ┌───►│    Running       │◄───┐
         │    └────┬────┬────┬───┘    │
         │         │    │    │        │
         │         │    │    │        │ user sends input
         │         │    │    ▼        │
         │         │    │  ┌─────────┴──┐
         │         │    │  │  Waiting   │
         │         │    │  └──────┬─────┘
         │         │    │         │
    resume│         │    │    pause│
         │    pause │    │         │
         │         │    │         │
         │         ▼    │         ▼
         │    ┌─────────┴─────────────┐
         └────┤       Paused          │
              └───────────────────────┘

              Running ──────► Completed  (claude 정상 종료)
              Running ──────► Failed     (에러 발생)
              Waiting ──────► Failed     (에러 발생)
              Creating ─────► Failed     (샌드박스 생성 실패)
```

### 5.2 전이 규칙 (가드 조건)

```go
// internal/session/state.go

// Transition은 상태 전이를 정의한다.
type Transition struct {
    From   Status
    To     Status
    Guard  func(s *Session) error  // nil이면 조건 없음
    Action func(s *Session) error  // 전이 시 실행할 액션
}

var transitions = []Transition{
    // Creating → Running
    {
        From:  StatusCreating,
        To:    StatusRunning,
        Guard: func(s *Session) error {
            if s.SandboxDir == "" {
                return errors.New("sandbox not initialized")
            }
            if s.terminal == nil || !s.terminal.IsRunning() {
                return errors.New("terminal not running")
            }
            return nil
        },
        Action: func(s *Session) error {
            s.StartedAt = time.Now()
            return nil
        },
    },

    // Running → Waiting
    {From: StatusRunning, To: StatusWaiting},

    // Waiting → Running
    {From: StatusWaiting, To: StatusRunning},

    // Running → Paused
    {
        From: StatusRunning,
        To:   StatusPaused,
        Action: func(s *Session) error {
            return s.terminal.Detach()
        },
    },

    // Waiting → Paused
    {
        From: StatusWaiting,
        To:   StatusPaused,
        Action: func(s *Session) error {
            return s.terminal.Detach()
        },
    },

    // Paused → Running
    {
        From:  StatusPaused,
        To:    StatusRunning,
        Guard: func(s *Session) error {
            if s.SandboxDir == "" {
                return errors.New("sandbox directory missing")
            }
            return nil
        },
    },

    // Running → Completed
    {
        From: StatusRunning,
        To:   StatusCompleted,
        Action: func(s *Session) error {
            s.CompletedAt = time.Now()
            return nil
        },
    },

    // Any → Failed
    {From: StatusCreating, To: StatusFailed},
    {From: StatusRunning,  To: StatusFailed},
    {From: StatusWaiting,  To: StatusFailed},
}
```

### 5.3 상태 감지 방법

| 전이 | 감지 방법 |
|------|----------|
| Creating → Running | `terminal.IsRunning()` == true |
| Running → Waiting | stdout에서 프롬프트 패턴 감지 (`❯`, `?`, 입력 대기 문구) |
| Running → Completed | Claude Code 프로세스 정상 종료 (exit code 0) |
| Running → Failed | 프로세스 비정상 종료 또는 타임아웃 |
| (사용자 액션) | Pause, Resume, Kill은 사용자 명시 요청 |

---

## 6. 샌드박스 보안 모델

### 6.1 디렉토리 구조

세션 생성 시 자동으로 구성되는 샌드박스 디렉토리:

```
~/.forge/sessions/{session-id}/
├── .claude/
│   └── settings.json         # Claude Code 퍼미션 (Policy에서 생성)
├── CLAUDE.md                  # 작업 지시사항 + 제약 조건
├── .gitignore                 # .claude/ 제외
└── (프로젝트 파일)             # git worktree 또는 빈 디렉토리
```

### 6.2 settings.json 생성 예시

Policy → settings.json 변환:

```json
// Policy: "restricted" 프리셋에서 생성된 settings.json
{
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Write(src/**)",
      "Edit(src/**)"
    ],
    "deny": [
      "Bash",
      "Agent"
    ]
  }
}
```

### 6.3 CLAUDE.md 생성 예시

```markdown
# Session: {title}

## Task
{사용자가 지정한 작업 설명}

## Constraints
- 수정 가능 파일: {allowedPaths}
- 토큰 예산: {tokenBudget} tokens
- 네트워크 접근: {허용/차단}
- 이 세션은 지정된 작업만 수행합니다.
- 작업 완료 시 결과를 요약하고 종료하세요.

## Working Directory
이 디렉토리가 작업 루트입니다.
상위 디렉토리에 접근하지 마세요.
```

### 6.4 보안 정책 프리셋

```go
// internal/sandbox/preset.go

var Presets = map[string]Policy{
    "readonly": {
        Name:        "readonly",
        Description: "읽기 전용 분석. 파일 수정 불가.",
        Allow: []Permission{
            {Tool: "Read"}, {Tool: "Glob"}, {Tool: "Grep"},
        },
        Deny: []Permission{
            {Tool: "Write"}, {Tool: "Edit"}, {Tool: "Bash"}, {Tool: "Agent"},
        },
        NetworkAccess: false,
    },

    "restricted": {
        Name:        "restricted",
        Description: "제한된 쓰기. 쉘 실행 차단.",
        Allow: []Permission{
            {Tool: "Read"}, {Tool: "Glob"}, {Tool: "Grep"},
            {Tool: "Write"}, {Tool: "Edit"},
        },
        Deny: []Permission{
            {Tool: "Bash"}, {Tool: "Agent"},
        },
        NetworkAccess: false,
    },

    "standard": {
        Name:        "standard",
        Description: "일반 개발 작업. 제한된 쉘 허용.",
        Allow: []Permission{
            {Tool: "Read"}, {Tool: "Glob"}, {Tool: "Grep"},
            {Tool: "Write"}, {Tool: "Edit"},
            {Tool: "Bash", Pattern: "npm test"},
            {Tool: "Bash", Pattern: "go test"},
            {Tool: "Bash", Pattern: "git diff"},
            {Tool: "Bash", Pattern: "git status"},
        },
        Deny: []Permission{
            {Tool: "Bash", Pattern: "rm -rf"},
            {Tool: "Bash", Pattern: "curl"},
            {Tool: "Bash", Pattern: "wget"},
            {Tool: "Agent"},
        },
        NetworkAccess: false,
    },

    "full": {
        Name:        "full",
        Description: "모든 도구 허용. 신뢰된 작업 전용.",
        Allow: []Permission{
            {Tool: "Read"}, {Tool: "Glob"}, {Tool: "Grep"},
            {Tool: "Write"}, {Tool: "Edit"}, {Tool: "Bash"},
            {Tool: "Agent"},
        },
        Deny:          []Permission{},
        NetworkAccess: true,
    },
}
```

### 6.5 보안 레이어 (VISION-v2 Level 1-2 구현)

```
┌────────────────────────────────────────────────────────┐
│ Level 1: 디렉토리 격리                                   │
│   └── ~/.forge/sessions/{id}/                           │
│   └── Claude Code는 이 디렉토리 안에서만 실행             │
│   └── 상위 디렉토리 접근은 settings.json으로 차단         │
├────────────────────────────────────────────────────────┤
│ Level 2: 설정 기반 제한 (핵심)                           │
│   └── .claude/settings.json → allow/deny 규칙           │
│   └── CLAUDE.md → 행동 제약 지시                         │
│   └── 프리셋으로 일관된 정책 적용                         │
├────────────────────────────────────────────────────────┤
│ Level 3: 프로세스 레벨 (Phase 1 범위)                    │
│   └── tmux 세션 내에서만 실행                             │
│   └── TUI 키 바인딩으로만 제어 (임의 명령 실행 불가)       │
│   └── 토큰 예산 초과 시 자동 종료                         │
└────────────────────────────────────────────────────────┘
```

---

## 7. 터미널 관리 (tmux 연동)

### 7.1 TmuxTerminal 구현 전략

tmux를 "세션 컨테이너"로 사용. PTY를 통해 I/O 캡처.

```
forge 프로세스
    │
    ├── tmux new-session -d -s "forge_{id}" -c {workdir} "claude {args}"
    │       └── tmux 세션 (백그라운드)
    │           └── claude code (AI 작업 수행)
    │
    ├── PTY (creack/pty)
    │   └── tmux attach-session -t "forge_{id}"
    │       └── I/O 캡처 (미리보기용)
    │
    └── tmux capture-pane -t "forge_{id}" -p
        └── 텍스트 기반 출력 캡처 (변경 감지용)
```

### 7.2 세션 이름 규칙

```
forge_{session-id 앞 8자}
예: forge_a1b2c3d4
```

- `forge_` 접두어로 다른 tmux 세션과 구분
- UUID 앞 8자로 충돌 방지 + 가독성

### 7.3 출력 변경 감지

```go
// internal/terminal/capture.go

type OutputTracker struct {
    lastHash [32]byte   // SHA-256 of last captured output
}

func (t *OutputTracker) HasChanged(currentOutput string) bool {
    hash := sha256.Sum256([]byte(currentOutput))
    changed := hash != t.lastHash
    t.lastHash = hash
    return changed
}
```

주기: 200ms마다 `capture-pane` 실행 → 해시 비교 → 변경 시 이벤트 발행

### 7.4 Attach/Detach 흐름

```
Attach:
  1. PTY 열기: pty.Start(exec.Command("tmux", "attach-session", "-t", name))
  2. goroutine A: PTY → stdout (세션 출력을 사용자에게 전달)
  3. goroutine B: stdin → PTY (사용자 입력을 세션에 전달)
  4. goroutine C: SIGWINCH 감지 → PTY 크기 조정
  5. 분리 키(Ctrl+Q) 감지 시 → Detach

Detach:
  1. goroutine A, B, C 정지
  2. PTY 닫기
  3. tmux 세션은 계속 실행 (백그라운드)
  4. 캡처 모드로 복귀 (preview용)
```

---

## 8. 데이터 흐름 및 동시성 모델

### 8.1 goroutine 구조

```
main goroutine
    │
    ├── BubbleTea 이벤트 루프 (UI)
    │   └── tea.Program.Run()
    │
    ├── SessionManager
    │   └── 각 세션마다:
    │       ├── captureLoop goroutine  (200ms 주기, 출력 캡처)
    │       └── statusLoop goroutine   (1s 주기, 프로세스 상태 확인)
    │
    ├── Monitor goroutine              (2s 주기, 메트릭 수집)
    │   └── 모든 활성 세션의 CPU/Mem/Token 수집
    │
    ├── EventBus goroutine             (이벤트 라우팅)
    │   └── 이벤트 발행 → 구독자들에게 전달
    │
    └── (선택) Daemon goroutine        (자동 응답, 상태 저장)
```

### 8.2 채널 통신 패턴

```go
// EventBus 내부 구현
type channelBus struct {
    subscribers map[Type][]chan Event
    mu          sync.RWMutex
    closed      bool
}

// UI가 이벤트를 수신하는 패턴
func (app *App) Init() tea.Cmd {
    return tea.Batch(
        app.listenEvents(),      // EventBus 구독
        app.tickPreview(),       // 200ms 미리보기 갱신
        app.tickMetrics(),       // 2s 메트릭 갱신
    )
}

// BubbleTea Cmd로 이벤트를 전달
func (app *App) listenEvents() tea.Cmd {
    return func() tea.Msg {
        event := <-app.eventCh   // 블로킹 수신
        return eventMsg(event)   // tea.Msg로 변환
    }
}
```

### 8.3 데이터 흐름도

```
사용자 키 입력
    │
    ▼
┌─────────────────────┐
│   BubbleTea Update  │
│   (UI 이벤트 루프)    │
└────┬────────────────┘
     │ 명령 dispatch
     ▼
┌─────────────────────┐
│   SessionManager    │
│   (세션 CRUD)        │
└────┬────────────────┘
     │
     ├── Create: Sandbox.Setup() → Terminal.Start()
     │           → EventBus.Publish(SessionCreated)
     │
     ├── Pause:  Terminal.Detach() → Sandbox.Preserve()
     │           → Store.Save() → EventBus.Publish(StatusChanged)
     │
     ├── Input:  Terminal.Write(data)
     │
     └── Kill:   Terminal.Stop() → Sandbox.Teardown()
                 → Store.Delete() → EventBus.Publish(StatusChanged)

     ┌─────────────────────┐
     │ captureLoop (200ms) │ ──► Terminal.CaptureOutput()
     └─────────────────────┘     → OutputTracker.HasChanged()
              │                  → EventBus.Publish(OutputChanged)
              ▼
     ┌─────────────────────┐
     │  BubbleTea Update   │ ──► Preview 패널 갱신
     └─────────────────────┘

     ┌─────────────────────┐
     │  Monitor (2s)       │ ──► gopsutil.Process(pid)
     └─────────────────────┘     → TokenParser.Parse(output)
              │                  → EventBus.Publish(MetricsUpdated)
              ▼
     ┌─────────────────────┐
     │  BubbleTea Update   │ ──► Monitor 패널 갱신
     └─────────────────────┘
```

### 8.4 동시성 안전 규칙

| 자원 | 보호 방식 | 이유 |
|------|----------|------|
| `sessions` map | `sync.RWMutex` | 다수 goroutine이 읽기, 소수가 쓰기 |
| 개별 Session | 상태 전이는 Manager를 통해서만 | 단일 진입점으로 일관성 보장 |
| EventBus subscribers | `sync.RWMutex` | 런타임 구독/해제 |
| Terminal PTY | goroutine 소유권 | Attach 시 전용 goroutine, Detach 시 반환 |
| Store 파일 I/O | `sync.Mutex` | 동시 쓰기 방지 |
| OutputTracker hash | atomic 또는 Mutex | captureLoop에서만 접근하므로 사실상 단일 goroutine |

---

## 9. 스토리지 및 영속화

### 9.1 파일 시스템 레이아웃

```
~/.forge/                          # 앱 루트 (XDG_DATA_HOME 대응 가능)
├── config.json                    # 글로벌 설정
├── state.json                     # 세션 상태 (직렬화된 세션 목록)
├── daemon.pid                     # 데몬 PID 파일
├── forge.log                      # 앱 로그
└── sessions/                      # 세션별 샌드박스 디렉토리
    ├── a1b2c3d4-.../
    │   ├── .claude/settings.json
    │   ├── CLAUDE.md
    │   └── (프로젝트 파일)
    └── e5f6g7h8-.../
        └── ...
```

### 9.2 state.json 스키마

```json
{
  "version": "1.0",
  "sessions": [
    {
      "id": "a1b2c3d4-...",
      "title": "리팩토링 auth 모듈",
      "task": "src/auth/ 디렉토리의 미들웨어를 리팩토링하세요",
      "status": "paused",
      "sandbox_dir": "~/.forge/sessions/a1b2c3d4-.../",
      "policy_name": "restricted",
      "project_path": "/Users/user/projects/my-app",
      "exit_code": 0,
      "error_msg": "",
      "created_at": "2026-03-26T10:00:00Z",
      "started_at": "2026-03-26T10:00:05Z",
      "updated_at": "2026-03-26T11:30:00Z",
      "completed_at": null
    }
  ]
}
```

### 9.3 복원 로직

프로세스 재시작 시:

```
1. state.json 로드
2. 각 세션에 대해:
   ├── Status == Paused → 그대로 유지 (재개 가능)
   ├── Status == Running/Waiting
   │   ├── tmux 세션 존재? → Terminal 재연결 (PTY 복원)
   │   └── tmux 세션 없음? → Status = Failed (비정상 종료)
   ├── Status == Completed/Failed → 그대로 유지 (기록 보존)
   └── Status == Creating → Status = Failed (중간 중단)
3. 활성 세션의 captureLoop/statusLoop 재시작
```

---

## 10. CLI 명령 구조

### 10.1 명령 트리

```
forge                              # TUI 실행 (기본)
forge new <title>                  # 새 세션 생성
  --task "작업 설명"                # 작업 내용
  --project /path/to/project       # 대상 프로젝트
  --policy restricted              # 보안 정책 (readonly/restricted/standard/full)
  --worktree                       # git worktree 사용
  --budget 50000                   # 토큰 예산
forge list                         # 세션 목록
  --status running                 # 상태 필터
  --json                           # JSON 출력
forge attach <id|title>            # 세션에 연결 (인터랙티브)
forge pause <id|title>             # 세션 일시정지
forge resume <id|title>            # 세션 재개
forge kill <id|title>              # 세션 종료
forge status [id|title]            # 상태 + 메트릭 표시
forge log <id|title>               # 세션 로그 출력
forge daemon start|stop|status     # 데몬 관리
forge config                       # 설정 편집
forge version                      # 버전 표시
```

### 10.2 TUI 키 바인딩

```
세션 목록:
  j/↓        다음 세션
  k/↑        이전 세션
  Enter/o    세션 Attach (인터랙티브 모드)
  n          새 세션 생성
  p          세션 일시정지
  r          세션 재개
  D          세션 종료 (확인 필요)
  Tab        탭 전환 (Preview/Metrics)

Attach 모드:
  Ctrl+Q     Detach (TUI로 복귀)

전역:
  ?          도움말
  q          앱 종료
```

---

## 11. TUI 레이아웃

```
┌─ Agent Forge ──────────────────────────────────────────────┐
│                                                            │
│ ┌─ Sessions ──────┐ ┌─ Preview ──────────────────────────┐ │
│ │                  │ │                                    │ │
│ │  ● auth-refactor │ │  Claude Code 실시간 출력            │ │
│ │  ⏸ api-design    │ │                                    │ │
│ │  ✱ test-coverage │ │  $ claude "src/auth 리팩토링..."    │ │
│ │  ✓ bug-fix-123   │ │                                    │ │
│ │                  │ │  ██████████████░░░░ 67% complete   │ │
│ │                  │ │                                    │ │
│ │                  │ │                                    │ │
│ │                  │ │                                    │ │
│ ├──────────────────┤ ├────────────────────────────────────┤ │
│ │ CPU: 12%  │ Mem: │ │ Tokens: 23,450 / 50,000           │ │
│ │ 145MB     │ Net:●│ │ Duration: 4m 32s                  │ │
│ └──────────────────┘ └────────────────────────────────────┘ │
│                                                            │
│ [n]New [Enter]Attach [p]Pause [r]Resume [D]Kill [?]Help    │
└────────────────────────────────────────────────────────────┘

상태 아이콘:
  ●  Running
  ✱  Waiting (사용자 입력 대기)
  ⏸  Paused
  ✓  Completed
  ✗  Failed
```

---

## 12. 의존성 목록

### 12.1 Go 모듈 의존성

```
require (
    github.com/charmbracelet/bubbletea    v1.x    // TUI 프레임워크
    github.com/charmbracelet/lipgloss     v1.x    // TUI 스타일링
    github.com/charmbracelet/bubbles      v0.x    // TUI 컴포넌트 (spinner, textinput 등)
    github.com/creack/pty                 v1.x    // PTY 관리
    github.com/shirou/gopsutil/v4         v4.x    // 프로세스 메트릭
    github.com/spf13/cobra               v1.x    // CLI 프레임워크
    github.com/google/uuid               v1.x    // UUID 생성
)
```

### 12.2 외부 도구 의존성

| 도구 | 최소 버전 | 용도 |
|------|----------|------|
| tmux | 3.0+ | 세션 관리 |
| claude | 2.0+ | AI CLI |
| git | 2.x | worktree (선택) |

---

## 13. 구현 마일스톤 (Phase 1 세분화)

### M1: 프로젝트 초기화 + 기본 구조 (1일)

**산출물:**
- `runtime/` Go 모듈 초기화 (`go mod init`)
- 패키지 구조 생성 (빈 파일)
- `config/` 패키지: 경로 해석, 설정 로드/저장
- CLI 진입점 (`cobra` 기본 설정)

**검증:** `go build ./cmd/forge` 성공, `forge version` 출력

### M2: 샌드박스 + 정책 엔진 (2일)

**산출물:**
- `sandbox/` 패키지: 디렉토리 생성, settings.json 생성, CLAUDE.md 생성
- `sandbox/preset.go`: 4개 프리셋 (readonly, restricted, standard, full)
- `sandbox/generator.go`: Policy → settings.json 변환

**검증:** `forge new --task "test" --policy restricted` → `~/.forge/sessions/{id}/` 디렉토리에 올바른 settings.json, CLAUDE.md 생성

### M3: 터미널 관리 (2일)

**산출물:**
- `terminal/` 패키지: Terminal 인터페이스 + TmuxTerminal 구현
- tmux 세션 생성/종료/캡처
- PTY 기반 Attach/Detach
- OutputTracker (SHA-256 변경 감지)

**검증:** tmux 세션에서 Claude Code 실행, 출력 캡처, Attach/Detach 동작

### M4: 세션 관리 + 상태 머신 (2일)

**산출물:**
- `session/` 패키지: Session, Manager, State, Store
- 상태 전이 규칙 + 가드 조건
- JSON 직렬화/역직렬화
- 프로세스 재시작 시 세션 복원

**검증:** 세션 생성 → 실행 → 일시정지 → 재개 → 종료 전체 lifecycle 동작

### M5: 이벤트 시스템 + 모니터링 (1일)

**산출물:**
- `event/` 패키지: EventBus (channel 기반 pub/sub)
- `monitor/` 패키지: CPU/Mem 수집 (gopsutil), 토큰 파싱
- captureLoop, statusLoop, metricsLoop 통합

**검증:** 실행 중 세션의 CPU/Mem/Token 수치가 실시간 갱신

### M6: TUI (3일)

**산출물:**
- `ui/` 패키지: BubbleTea 앱
- 세션 목록, 미리보기 패널, 모니터 패널, 메뉴
- 키 바인딩, 오버레이 (생성 입력, 확인 다이얼로그, 도움말)
- Attach 모드 (Ctrl+Q detach)

**검증:** TUI에서 세션 CRUD, 실시간 미리보기, 메트릭 표시, Attach/Detach

### M7: CLI 명령 + 데몬 (1일)

**산출물:**
- `cmd/forge/` CLI 명령 전체 구현
- `daemon/` 패키지: 백그라운드 데몬 (자동 상태 저장)
- `forge daemon start/stop/status`

**검증:** CLI로 세션 관리, 데몬 시작/중지

---

## 14. v1 방법론 통합 포인트

Core Engine은 기존 agent-forge v1의 방법론을 CLAUDE.md 생성 시 주입할 수 있다:

```
agent-forge v1 자산              Core Engine 활용
───────────────────              ────────────────
phases/ (워크플로우)          →   CLAUDE.md "## Workflow" 섹션에 주입
dist/skills/ (스킬)           →   향후 Claude Code --skill 연동
delta-logs/ (컨텍스트)        →   CLAUDE.md "## Context" 섹션에 주입
tools/ (MCP 서버)             →   향후 .mcp.json 자동 설정
```

이 통합은 Phase 1의 필수 범위가 아니며, 샌드박스의 CLAUDE.md generator가
커스텀 Instructions를 지원하는 것으로 확장점을 보장한다.

---

## 15. 향후 확장 준비

Phase 1 설계에서 향후 Phase를 위해 열어둔 확장점:

| 확장점 | Phase | 준비 |
|--------|-------|------|
| Terminal 인터페이스 | 2+ | ContainerTerminal, RemoteTerminal 구현 가능 |
| Policy 커스텀 정의 | 2 | Policy 구조체가 YAML/JSON 직렬화 지원 |
| 멀티 모델 | 2 | TerminalConfig.Command로 codex, gemini 지정 가능 |
| API 서버 | 4 | `pkg/api/` 패키지로 gRPC/HTTP 서비스 구현 |
| 웹 GUI | 4 | EventBus를 WebSocket으로 브릿지 |
| Orchestrator | 3 | SessionManager.Create()를 프로그래밍적으로 호출 |
| Tool Registry | 2 | sandbox의 Policy.Allow에 MCP 도구 추가 |
