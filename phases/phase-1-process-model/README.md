# Phase 1: 프로세스 모델 추출

## 목표

claude-config의 프로세스 모델을 현재 SuperClaude 환경에 통합.
코드나 파일이 아닌, **원칙과 규약**만 추출한다.

## 배경

현재 환경(SuperClaude)은 도구는 충분하지만 프로세스가 부족하다:
- 커맨드(`/sc:*`)와 에이전트는 있지만, "언제 어떤 순서로 사용하는가"가 명확하지 않다
- 코드 리뷰 에이전트는 있지만, 심각도 기준과 반복 규칙이 없다
- 문서화 규약은 있지만, Temporal 오염 감지가 없다

claude-config이 이 문제를 해결하는 방식:
- QR 3-Tier 규칙으로 심각도 기준 명확화
- Temporal 규칙으로 문서 품질 구조적 보장
- 복잡도 기반 워크플로우 분기로 오버엔지니어링 방지
- 컨벤션 계층으로 규칙 간 충돌 해결

## 작업 항목

### 1.1 QR 3-Tier 규칙

**출처**: claude-config의 `conventions/severity.md`, `agents/quality-reviewer.md`

정의할 것:
- **MUST** (절대): 놓치면 복구 불가능한 것
  - 예: 보안 취약점, 데이터 손실, 결정 로그 누락
- **SHOULD** (권장): 유지보수 부채
  - 예: God Object, 중복 로직, 불일치 에러 처리
- **COULD** (선택): 자동 수정 가능한 것
  - 예: 데드 코드, 포매터 수정 가능 항목

반복별 디에스컬레이션:
- iter 1-2: 전체 차단
- iter 3-4: MUST + SHOULD
- iter 5+: MUST만 (무한 루프 방지)

### 1.2 Temporal 규칙

**출처**: claude-config의 `conventions/temporal.md`

"시간 없는 현재" 원칙 — 코멘트는 코드를 처음 만나는 독자의 관점에서 작성.

5가지 감지 휴리스틱:

| 유형 | 오염된 코멘트 | 올바른 코멘트 |
|------|-------------|-------------|
| 변경 참조 | "Added mutex for thread safety" | "Mutex serializes concurrent access" |
| 베이스라인 참조 | "Replaces old approach" | "Thread-safe: each goroutine independent" |
| 위치 지시 | "Insert before validation" | (삭제 — diff가 위치를 인코딩) |
| 계획 아티팩트 | "TODO: add later" | (삭제 또는 즉시 구현) |
| 의도 노출 | "Chose polling for reliability" | "Polling: 30% webhook failures observed" |

### 1.3 워크플로우 분기

복잡도 판정 기준:

| 기준 | Micro | Standard | Full |
|------|-------|----------|------|
| 파일 수 | 1-2 | 3-10 | 10+ |
| 변경 유형 | 단일 관심사 | 다중 관심사 | 아키텍처 변경 |
| 의존성 영향 | 없음 | 제한적 | 넓음 |
| QR 필요성 | 생략 | 1회 | 마일스톤별 |

### 1.4 컨벤션 계층

4-tier 우선순위 (Phase 2에서 Tier 1.5 추가):

```
Tier 1:   사용자 명시 지시 (절대 우선)
Tier 1.5: 도메인 프로필 (Phase 2에서 추가)
Tier 2:   프로젝트 문서 (CLAUDE.md, README.md)
Tier 3:   기본 규약 (이 Phase에서 정의)
```

충돌 해결: 상위 Tier가 항상 승리. 같은 Tier 내에서는 더 구체적인 규칙이 승리.

## 산출물

| 문서 | 내용 |
|------|------|
| [qr-rules.md](qr-rules.md) | MUST/SHOULD/COULD 심각도, 반복 디에스컬레이션, 리뷰 프로토콜, Intent Markers |
| [temporal-rules.md](temporal-rules.md) | 시간 없는 현재 원칙, 5가지 감지 휴리스틱, 적용 범위 |
| [workflow-tiers.md](workflow-tiers.md) | Micro/Standard/Full 3단계, 복잡도 판정, 도메인 조정 |
| [convention-tiers.md](convention-tiers.md) | 4-tier 우선순위, 충돌 해결, 문서화 요구사항 |

## 완료 기준

- [x] QR 규칙 문서가 작성되어 리뷰 시 참조 가능
- [x] Temporal 규칙이 문서화 가이드라인에 포함
- [x] 복잡도 판정 기준이 명확하게 정의
- [x] 컨벤션 4-tier 계층이 정의되고, 충돌 해결 규칙이 존재
- [ ] 실제 프로젝트에서 1회 이상 적용 테스트

## 다음 단계

Phase 1 완료 후:
- Phase 2 (도메인 프로필)와 Phase 3 (컨텍스트 관리) 병렬 착수 가능
- Phase 4 (측정)의 메트릭 정의 착수 가능
