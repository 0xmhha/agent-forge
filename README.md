# Agent Forge

LLM 에이전트 기반 소프트웨어 개발을 위한 프로세스 프레임워크.

도구(tool)가 아닌 **방법론(methodology)**에 집중한다.
에이전트가 코드를 더 빠르게 생성하는 것이 아니라,
**지속 가능한 품질로 코드를 생성**하는 체계를 구축한다.

## 문제 정의

LLM 기반 개발에서 반복적으로 관찰되는 실패 패턴:

1. **기술 부채의 보이지 않는 축적** — LLM은 자신이 만든 중복, God Function, 불일치를 감지하지 못한다
2. **컨텍스트 분산** — 코드가 누적될수록 검토량은 증가하지만, 토큰 예산은 고정이다
3. **도메인 무관심** — 범용 에이전트는 금융의 규정 준수와 게임의 성능 최적화를 구분하지 못한다
4. **측정 부재** — 어떤 접근이 효과적인지 정량적으로 알 수 없다

## 접근 방식

기존 운영 환경(SuperClaude)을 유지하면서, 부족한 레이어를 추가한다:

| 레이어 | 구현 상태 | 목적 |
|--------|:---------:|------|
| 프로세스 모델 | **완료** | 계획-실행-검증의 구조적 분리 (Tier 분기, QR Gate) |
| 도메인 프로필 | **완료** | 프로젝트별 우선순위/규약 커스터마이징 (YAML 스키마) |
| 컨텍스트 관리 | **완료** | 토큰 효율적 누적 지식 관리 (delta-log, rolling-summary) |
| 측정 파이프라인 | **설계 완료** | 비용/품질 정량 분석 (데이터 수집 대기) |

## 핵심 워크플로우

```
/complexity → 코딩 → /milestone
```

| Tier | 파일 수 | 절차 |
|------|---------|------|
| Micro | 1-2 | 직접 실행 → 커밋 |
| Standard | 3-10 | 계획 → 실행 → QR 1회 → handoff → 커밋 |
| Full | 10+ | 마일스톤 자동 분해 → 마일스톤별 (실행 → QR) → handoff → 커밋 |

## 적용된 에이전트 패턴

| 패턴 | 구현체 | 설명 |
|------|--------|------|
| 순차 (Sequential) | `/milestone` | QR → delta-log → handoff → 토큰 → 커밋 |
| 리뷰/비판 (Review & Critique) | `/qr-gate` | MUST/SHOULD/COULD + 자동 수정 루프 (최대 2회) |
| 인간 참여형 (Human-in-the-Loop) | Tier 분기 | Standard/Full에서 계획 확인 후 실행 |
| 코디네이터 (Coordinator) | `/milestone` | Tier별 동적 라우팅 |
| 병렬 (Parallel) | `/check-reviews` | pending + todo + done 병렬 MCP 호출 |
| 반복적 개선 (Iterative) | `/qr-gate` | 자동 수정 루프 + 반복별 디에스컬레이션 |
| 계층적 분해 (Hierarchical) | `/complexity` | Full Tier 자동 마일스톤 분해 + Wave 실행 |

상세 분석: [docs/pattern-analysis.md](docs/pattern-analysis.md)

## 사용 가능한 명령

### Core Skills (기본 설치)

| 명령 | 용도 |
|------|------|
| `/complexity` | 복잡도 평가, Tier 추천, Full시 마일스톤 자동 분해 |
| `/qr-gate` | Quality Review (자동 수정 루프 포함, 최대 2회) |
| `/delta-log` | delta-log 엔트리 + rolling-summary 생성 |
| `/milestone` | 전체 완료 워크플로우 일괄 실행 (handoff 포함) |
| `/handoff` | 세션 인수인계 문서 생성 |

### Review Skills (`--full` 설치 시)

| 명령 | 용도 |
|------|------|
| `/check-reviews` | Gmail + GitHub에서 신규 코드 리뷰 요청 병렬 수집 |
| `/do-review` | code-reviewer sub-agent로 코드 리뷰 실행 |

## MCP 도구 플랫폼

### workspace-mcp (24 tools)

Gmail + GitHub 모니터링 및 코드 리뷰 자동화 MCP 서버.

| 카테고리 | 도구 수 | 주요 기능 |
|----------|---------|----------|
| Gmail | 5 | 메일 조회, 검색, Jira 티켓 감지, 액션 분류 |
| GitHub | 7 | 이슈/PR 조회, CI 상태, PR 리뷰 환경 셋업 |
| Review | 9 | 리뷰 대기/완료 관리, todo 생성, 에이전트 폴링 |
| Task | 3 | 태스크 목록, 동기화, 상태 갱신 |

### token-monitor-mcp (5 tools)

토큰 사용량 추적 및 비용 분석 MCP 서버.

| 도구 | 기능 |
|------|------|
| `token_session_list` | 전체 세션 목록 |
| `token_session_summary` | 세션별 토큰 상세 |
| `token_cost_check` | USD 비용 조회 |
| `token_session_export` | agent-forge 포맷 내보내기 |
| `token_monitor_version` | 바이너리 버전 |

## 설치

```bash
# 대상 프로젝트에 설치 (core skills: 5개)
./dist/install.sh /path/to/target-project

# 리뷰 스킬 포함 설치 (all skills: 7개)
./dist/install.sh /path/to/target-project --full

# 전역 설치 (모든 프로젝트에 core skills 적용)
./dist/install.sh /path/to/target-project --global
```

설치 후 30/60/90 온보딩 가이드가 출력된다.

## 프로젝트 구조

```
agent-forge/
├── dist/                              배포물 (대상 프로젝트 설치용)
│   ├── install.sh                     설치 스크립트
│   ├── skills/                        7개 스킬
│   │   ├── complexity/                복잡도 평가 + 마일스톤 분해
│   │   ├── qr-gate/                   품질 검증 + 자동 수정 루프
│   │   ├── delta-log/                 마일스톤 기록
│   │   ├── milestone/                 완료 워크플로우 (코디네이터)
│   │   ├── handoff/                   세션 인수인계
│   │   ├── check-reviews/             리뷰 요청 수집 (병렬)
│   │   └── do-review/                 코드 리뷰 실행 (sub-agent)
│   ├── hooks/                         pre-commit QR, session-end checklist
│   └── templates/                     CLAUDE.md 템플릿
├── phases/                            방법론 문서 (Phase 1-4)
│   ├── phase-1-process-model/         QR 규칙, Temporal 규칙, Tier 정의
│   ├── phase-2-domain-profiles/       스키마, 3개 예시 프로필, 통합 가이드
│   ├── phase-3-context-management/    델타 로그, 롤링 요약, 병합 규칙
│   └── phase-4-measurement/           17개 메트릭, 수집 가이드, 분석 플레이북
├── tools/                             MCP 서버 구현
│   ├── workspace-mcp/                 Gmail + GitHub + 리뷰 자동화 (Python)
│   └── token-monitor-mcp/             토큰 모니터링 (Go binary + Python wrapper)
├── delta-logs/                        프로젝트 마일스톤 기록
│   ├── M0-baseline.json               초기 상태
│   ├── M6-handler-wiring.json         최근 마일스톤
│   └── rolling-summary.md             누적 변경 요약
├── docs/                              분석 및 설계 문서
│   ├── ANALYSIS.md                    4개 프로젝트 배경 분석
│   ├── ARCHITECTURE.md                시스템 아키텍처
│   ├── ROADMAP.md                     4단계 실행 로드맵
│   ├── pattern-analysis.md            에이전트 패턴 적용 분석
│   ├── agent-pattern.md               Google Cloud 에이전트 패턴 정리
│   └── references/                    참고 연구/논문
└── CLAUDE.md                          프로젝트 방법론 설정
```

## 개발 명령어

```bash
# workspace-mcp 테스트
cd tools/workspace-mcp && uv run python -m pytest -q

# token-monitor-mcp 테스트
cd tools/token-monitor-mcp && uv run python -m pytest -q

# workspace-mcp 서버 실행
cd tools/workspace-mcp && make server

# OAuth 셋업 (최초 1회)
cd tools/workspace-mcp && make setup
```

## 4단계 로드맵

```
Phase 1: 프로세스 모델 ─────── ✅ 완료
         QR 게이트, Temporal 규칙, 워크플로우 Tier, 컨벤션 계층

Phase 2: 도메인 프로필 ─────── ✅ 완료
         YAML 스키마, 3개 예시 프로필, 통합 메커니즘

Phase 3: 컨텍스트 관리 ─────── ✅ 완료
         delta-log 시스템, rolling-summary, 병합 규칙

Phase 4: 측정 파이프라인 ───── 🔧 설계 완료 (데이터 수집 대기)
         17개 메트릭, 수집 가이드, 분석 플레이북
```

각 Phase의 상세 내용은 [docs/ROADMAP.md](docs/ROADMAP.md) 참조.

## 배경 연구

이 프로젝트는 다음 오픈소스 프로젝트들의 분석에서 출발했다:

- [claude-config](https://github.com/solatis/claude-config) — 프로세스 엔지니어링 접근 (계획-실행-QR 게이트)
- [SuperClaude](https://github.com/nickbaumann98/superClaude) — 커맨드 체계 + 에이전트 팜
- [Everything Claude Code](https://github.com/anthropics/courses) — 넓은 에이전트/스킬 생태계
- [Aperant](https://github.com/aperant) — 완전 자율 실행

각 프로젝트의 상세 분석: [docs/ANALYSIS.md](docs/ANALYSIS.md)
