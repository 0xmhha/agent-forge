# 실행 로드맵

4개의 Phase로 구성. 각 Phase는 독립적으로 가치를 제공하며, 이전 Phase의 결과물 위에 구축된다.

---

## Phase 1: 프로세스 모델 추출 — ✅ 완료

**목표**: claude-config의 프로세스 모델(계획-실행-검증 분리)을 현재 SuperClaude 환경에 통합

**선행 조건**: 없음 (첫 번째 단계)

**산출물**:
- QR 3-Tier 규칙이 통합된 코드 리뷰 가이드라인
- Temporal 규칙이 포함된 문서화 규약
- 복잡도 기반 3-tier 워크플로우 분기 기준
- 컨벤션 계층 정의 (4-tier: 사용자 > 도메인 > 프로젝트 > 기본)

**작업 항목**:

### 1.1 QR 규칙 정의
- [x] MUST/SHOULD/COULD 심각도 분류 기준 정의 → `phases/phase-1-process-model/qr-rules.md`
- [x] 반복별 디에스컬레이션 규칙 정의 (iter별 차단 수준) → `dist/skills/qr-gate/SKILL.md`
- [x] 현재 code-reviewer 에이전트와의 통합 방안 설계 → `/qr-gate` 스킬로 구현

### 1.2 Temporal 규칙
- [x] "시간 없는 현재" 원칙 문서화 → `phases/phase-1-process-model/temporal-rules.md`
- [x] 5가지 감지 휴리스틱 정의 (변경 참조, 베이스라인 참조, 위치 지시, 계획 아티팩트, 의도 노출)
- [x] 문서화 규약에 통합 → `/delta-log`, `/handoff` 스킬에 적용

### 1.3 워크플로우 분기
- [x] 복잡도 판정 기준 정의 (파일 수, 변경 범위, 아키텍처 영향) → `phases/phase-1-process-model/workflow-tiers.md`
- [x] 3-tier 워크플로우 정의:
  - Micro (1-2 파일): Developer 직접 실행
  - Standard (3-10 파일): 계획 → 실행, QR 1회
  - Full (10+ 파일): 자동 마일스톤 분해 → 마일스톤별 QR
- [x] 자동 분기 판정 로직 설계 → `/complexity` 스킬

### 1.4 컨벤션 계층
- [x] 4-tier 컨벤션 계층 정의 → `phases/phase-1-process-model/convention-tiers.md`
- [x] 계층 간 충돌 해결 규칙 정의
- [x] 기본 규약 세트 (structural defaults) 정의

**완료 기준**: ✅ 문서화된 프로세스 모델이 존재하고, 실제 프로젝트에 적용 가능한 형태

---

## Phase 2: 도메인 프로필 시스템 — ✅ 완료

**목표**: YAML 기반 도메인 프로필로 에이전트 행동을 프로젝트별 커스터마이징

**선행 조건**: Phase 1 (컨벤션 계층이 정의되어야 도메인 프로필이 삽입될 위치가 확정)

**산출물**:
- 도메인 프로필 스키마 (YAML)
- 3개 이상의 예시 프로필 (fintech, game-dev, startup-mvp)
- 프로필이 에이전트 행동에 영향을 미치는 메커니즘

**작업 항목**:

### 2.1 프로필 스키마 설계
- [x] 우선순위 매트릭스 정의 (안전성, 성능, 규정준수, 속도, 유지보수성) → `phases/phase-2-domain-profiles/schema.yaml`
- [x] 규약 오버라이드 구조 정의 (테스트 전략, 리뷰 깊이, 문서화 수준)
- [x] 도메인 지식 구조 정의 (용어 사전, 금지/필수 패턴)
- [x] 워크플로우 커스터마이징 구조 정의

### 2.2 예시 프로필 작성
- [x] fintech 프로필 (규정 준수 최우선, 감사 로그 필수, 부동소수점 통화 금지) → `profiles/fintech.yaml`
- [x] game-dev 프로필 (성능 최우선, hot path 최적화, 메모리 풀링) → `profiles/game-dev.yaml`
- [x] startup-mvp 프로필 (속도 최우선, QR 최소화, 문서화 최소) → `profiles/startup-mvp.yaml`

### 2.3 통합 메커니즘
- [x] 도메인 프로필이 컨벤션 계층에 삽입되는 방식 정의 → `phases/phase-2-domain-profiles/integration-guide.md`
- [x] 에이전트가 프로필을 읽고 행동을 조정하는 프로토콜 정의 → `/qr-gate`, `/complexity` 스킬에 통합
- [ ] 프로필 간 전환 메커니즘 (다중 도메인 프로젝트) — 미구현

**완료 기준**: ✅ 도메인 프로필을 교체하면 동일 에이전트가 다른 기준으로 리뷰하는 것이 관찰 가능

---

## Phase 3: 컨텍스트 관리 레이어 — ✅ 완료

**목표**: 토큰 효율적 누적 컨텍스트 관리 시스템 구축

**선행 조건**: Phase 1 (프로세스 모델의 마일스톤 구조가 있어야 델타 엔트리 생성 시점이 확정)

**산출물**:
- 델타 로그 시스템 (ACE 패턴)
- 구조적 롤링 요약
- 결정론적 병합 규칙

**작업 항목**:

### 3.1 델타 로그 시스템
- [x] 델타 엔트리 스키마 정의 (변경 파일, 결정, 교훈, 다음 단계) → `phases/phase-3-context-management/delta-schema.json`
- [x] 마일스톤 완료 시 자동 델타 생성 프로토콜 → `/delta-log` 스킬
- [x] 결정론적 병합 규칙 (LLM 호출 없이 구조적 병합) → `phases/phase-3-context-management/merge-rules.md`
- [x] 델타 로그 → 컨텍스트 주입 메커니즘 → `phases/phase-3-context-management/context-injection.md`

### 3.2 롤링 요약
- [x] 구조적 섹션 정의 (수정된 파일, 결정, 미해결 사항, 다음 단계) → `rolling-summary-template.md`
- [x] 컨텍스트 잘림 시 증분 요약 생성 규칙
- [x] 요약 품질 검증 방법 (정보 손실 감지)

### 3.3 변경 감지 (선택적)
- [x] 파일 해시 기반 변경 추적 방식 조사 → `phases/phase-3-context-management/change-detection.md`
- [x] 변경된 파일만 재요약하는 파이프라인 설계
- [ ] 캐싱 전략 (콘텐츠 해시 → 요약 매핑) — 설계만 완료, 구현 미착수

**완료 기준**: ✅ delta-logs/에 M0~M6 기록 존재, rolling-summary.md로 컨텍스트 유지됨

**참고**: [references/context-management.md](references/context-management.md)

---

## Phase 4: 측정 파이프라인 — 🔧 설계 완료

**목표**: 비용/품질 데이터를 정량적으로 추적하여 개선 루프 구축

**선행 조건**: Phase 1-3 중 하나 이상이 동작해야 측정 대상이 존재

**산출물**:
- 세션별 토큰 소비 추적 구조
- QR 통과율/재작업 횟수 메트릭
- 워크플로우별 비용-품질 상관관계 분석

**작업 항목**:

### 4.1 메트릭 정의
- [x] 핵심 메트릭 정의 (17개) → `phases/phase-4-measurement/metrics-definition.md`
  - 토큰 소비 (입력/출력/캐시, 단계별)
  - QR 통과율 (첫 시도 통과 vs 재시도)
  - 재작업 횟수 (같은 파일을 몇 번 수정했는가)
  - 에스컬레이션 빈도 (모델 업그레이드 횟수)
- [x] 메트릭 수집 시점 정의

### 4.2 수집 메커니즘
- [x] ccusage/token-monitor 연동 방안 조사 → `phases/phase-4-measurement/collection-guide.md`
- [x] cc-history JSONL 파서 설계
- [x] 수집 템플릿 정의 → `phases/phase-4-measurement/templates/session-log.json`
- [ ] 자동 수집 파이프라인 구현 — 미착수

### 4.3 분석 및 피드백
- [x] 분석 플레이북 정의 (4개 절차) → `phases/phase-4-measurement/analysis-playbook.md`
  - 워크플로우별 비교 (Micro vs Standard vs Full)
  - 도메인 프로필별 비교 (fintech vs startup-mvp)
  - QR 영향 분석
  - 컨텍스트 관리 효과 분석
- [ ] 실제 데이터 수집 (10+ 세션) — 대기 중
- [ ] 정량적 결론 도출 — 데이터 수집 후 진행

**완료 기준**: ⏳ "Phase 1 프로세스 적용 시 토큰 X% 증가, 재작업 Y% 감소" 형태의 정량적 결론 도출 가능

**다음 단계**: token-monitor-mcp를 활용하여 실제 세션 데이터 수집 시작

---

## Phase 간 의존성

```
Phase 1 ──────┬──────► Phase 3
(프로세스) ✅  │        (컨텍스트) ✅
              │
              ├──────► Phase 2
              │        (도메인) ✅
              │
              └──────► Phase 4 ◄── Phase 2, 3
                       (측정) 🔧
```

- Phase 1은 다른 모든 Phase의 기반 — ✅ 완료
- Phase 2와 3은 Phase 1 이후 병렬 진행 가능 — ✅ 둘 다 완료
- Phase 4는 측정 대상(Phase 1-3)이 있어야 의미 있음 — 🔧 설계 완료, 데이터 수집 대기

---

## 고도화 현황 (에이전트 패턴 적용)

Phase 1-3 완료 후 [pattern-analysis.md](pattern-analysis.md) 기반으로 에이전트 패턴을 적용하여 고도화를 진행했다:

| 적용 패턴 | 구현체 | 상태 |
|-----------|--------|:----:|
| 순차 + 코디네이터 | `/milestone` 동적 라우팅 | ✅ |
| 리뷰/비판 + 반복적 개선 | `/qr-gate` 자동 수정 루프 (최대 2회) | ✅ |
| 계층적 분해 | `/complexity` Full Tier 마일스톤 자동 분해 | ✅ |
| 병렬 | `/check-reviews` 병렬 MCP 호출 | ✅ |
| 인간 참여형 | Tier 분기 + Full Tier 마일스톤 확인 | ✅ |
| 세션 관리 | `/handoff` 인수인계 스킬 + `/milestone` handoff 통합 | ✅ |

상세 분석: [pattern-analysis.md](pattern-analysis.md)

---

## 진행 원칙

1. **각 Phase는 독립적 가치를 제공한다** — Phase 1만 완료해도 현재보다 개선
2. **문서 먼저, 구현 나중** — 원칙과 규칙을 먼저 정의하고, 코드는 그 다음
3. **측정 가능한 완료 기준** — "느낌"이 아닌 관찰 가능한 결과로 판정
4. **점진적 복잡도** — 간단한 것부터 시작하여 필요에 따라 확장

---

## 남은 작업

| 항목 | 우선순위 | 설명 |
|------|:--------:|------|
| Phase 4 데이터 수집 | 높음 | 10+ 세션 데이터로 정량 분석 시작 |
| 다중 도메인 프로필 전환 | 중간 | 하나의 프로젝트에서 도메인 전환 메커니즘 |
| workspace-mcp batch 병렬화 | 중간 | batch scheduler에 병렬 처리 옵션 |
| Self-improvement loop | 낮음 | 스킬 품질 자동 측정 체계 |
| Agent Teams + worktree | 낮음 | Full Tier 마일스톤 병렬 실행 |
| ReAct 디버깅 스킬 | 낮음 | 구조화된 디버깅 워크플로 |
| 콘텐츠 해시 캐싱 | 낮음 | 변경 감지 최적화 (Merkle Tree) |
