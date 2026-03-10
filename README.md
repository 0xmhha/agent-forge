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

기존 운영 환경(SuperClaude)을 유지하면서, 부족한 3개 레이어를 추가한다:

| 레이어 | 출처 | 목적 |
|--------|------|------|
| 프로세스 모델 | claude-config에서 추출 | 계획-실행-검증의 구조적 분리 |
| 도메인 프로필 | 신규 설계 | 프로젝트별 우선순위/규약 커스터마이징 |
| 컨텍스트 관리 | 신규 구축 (ACE, Merkle Tree, Meta-RAG 기반) | 토큰 효율적 누적 지식 관리 |
| 측정 파이프라인 | token-monitor 연동 | 비용/품질 정량 분석 |

## 4단계 로드맵

```
Phase 1: 프로세스 모델 추출
         claude-config의 QR 게이트, Temporal 규칙, 컨벤션 계층을
         현재 SuperClaude 환경에 통합

Phase 2: 도메인 프로필 시스템
         YAML 기반 도메인 프로필로 에이전트 행동을 프로젝트별 커스터마이징

Phase 3: 컨텍스트 관리 레이어
         ACE 델타 엔트리 + Merkle 변경 감지 + 계층적 검색으로
         토큰 효율적 누적 컨텍스트 관리

Phase 4: 측정 파이프라인
         토큰 소비, QR 통과율, 재작업 횟수를 추적하여
         데이터 기반 개선 루프 구축
```

각 Phase의 상세 내용은 [docs/ROADMAP.md](docs/ROADMAP.md) 참조.

## 프로젝트 구조

```
agent-forge/
├── docs/                          분석 및 설계 문서
│   ├── ANALYSIS.md                프로젝트 배경 분석
│   ├── ARCHITECTURE.md            시스템 아키텍처
│   ├── ROADMAP.md                 4단계 실행 로드맵
│   └── references/                참고 연구/논문
│       └── context-management.md  컨텍스트 관리 기술 레퍼런스
├── phases/                        단계별 구현
│   ├── phase-1-process-model/     프로세스 모델 추출
│   ├── phase-2-domain-profiles/   도메인 프로필 시스템
│   ├── phase-3-context-management/ 컨텍스트 관리 레이어
│   └── phase-4-measurement/       측정 파이프라인
└── README.md
```

## 배경 연구

이 프로젝트는 다음 오픈소스 프로젝트들의 분석에서 출발했다:

- [claude-config](https://github.com/solatis/claude-config) — 프로세스 엔지니어링 접근 (계획-실행-QR 게이트)
- [SuperClaude](https://github.com/nickbaumann98/superClaude) — 커맨드 체계 + 에이전트 팜
- [Everything Claude Code](https://github.com/anthropics/courses) — 넓은 에이전트/스킬 생태계
- [Aperant](https://github.com/aperant) — 완전 자율 실행

각 프로젝트의 상세 분석: [docs/ANALYSIS.md](docs/ANALYSIS.md)
