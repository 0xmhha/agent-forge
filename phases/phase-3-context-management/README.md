# Phase 3: 컨텍스트 관리 레이어

## 목표

토큰 효율적 누적 컨텍스트 관리 시스템 구축.
코드가 누적될수록 검토량은 증가하지만, 토큰 소비는 선형 증가하지 않도록.

## 배경

### 핵심 문제

```
마일스톤 1: 5 파일 변경 → 5 파일 컨텍스트
마일스톤 2: 5 파일 변경 → 10 파일 컨텍스트 (이전 + 현재)
마일스톤 3: 5 파일 변경 → 15 파일 컨텍스트
...
마일스톤 N: 5 파일 변경 → 5N 파일 컨텍스트 ← 토큰 폭발
```

필요한 것: 마일스톤 N에서도 "현재 작업에 필요한 핵심 컨텍스트"만 효율적으로 전달.

### 3가지 하위 문제

1. **압축**: 같은 정보를 더 적은 토큰으로 표현
2. **선택**: 현재 작업에 필요한 것만 포함
3. **지속성**: 컨텍스트에서 빠진 정보를 나중에 복구 가능하게

## 설계

### 3.1 델타 로그 시스템 (ACE 패턴)

매 마일스톤 완료 시 "델타 엔트리"를 생성하여 누적.

**델타 엔트리 스키마**:

```json
{
  "milestone": "M3",
  "timestamp": "2026-03-10T15:30:00Z",
  "files_changed": [
    {"path": "src/auth.py", "action": "modified", "summary": "JWT 검증 로직 추가"}
  ],
  "decisions": [
    {"decision": "JWT > 세션", "rationale": "무상태 우선, 수평 확장 고려"}
  ],
  "lessons": [
    "bcrypt 라이브러리가 M1에서 이미 설치됨 — 추가 의존성 불필요"
  ],
  "unresolved": [
    "토큰 갱신 전략 미확정"
  ],
  "next_steps": [
    "토큰 갱신 엔드포인트 구현"
  ]
}
```

**파일명 컨벤션**: `M{N}-{slug}.json`
- `{N}`: 마일스톤 번호 (0-padded 불필요)
- `{slug}`: 작업 내용 kebab-case 요약
- 예: `M0-baseline.json`, `M6-handler-wiring.json`, `M12-auth-refactor.json`

**M0 baseline 엔트리**:
M0는 프로젝트 초기 상태를 기록하는 특수 엔트리이다. 일반 마일스톤과 달리 "증분"이 아닌 "전체 상태"를 기록한다.
- `files_changed`: 프로젝트 시작 시점의 모든 파일 (action: "created")
- `decisions`: 프로젝트 시작 전에 이미 내린 결정 (기술 스택 선택 등)
- `context_snapshot`: 초기 프로젝트 규모
- M0는 이후 마일스톤의 비교 기준선(baseline)으로 사용됨

**병합 규칙** (결정론적, LLM 호출 없음):
- `files_changed`: 같은 파일의 이전 엔트리를 최신으로 교체
- `decisions`: 항상 추가 (결정은 삭제하지 않음)
- `lessons`: 중복 제거 후 추가
- `unresolved`: 해결된 항목은 제거, 새 항목 추가
- `next_steps`: 완료된 항목 제거, 새 항목 추가

**왜 결정론적인가**:
LLM으로 병합하면 반복할수록 세부사항이 사라진다 (context collapse).
규칙 기반 병합은 환각 없이 정보를 보존한다.

### 3.2 구조적 롤링 요약

컨텍스트 잘림 시에만 동작하는 요약 시스템.

**강제 섹션**:
```markdown
## 수정된 파일
- src/auth.py: JWT 검증 (M3에서 추가)
- src/models/user.py: role 필드 (M2에서 추가)

## 핵심 결정
- JWT > 세션: 무상태 우선
- bcrypt > argon2: 기존 의존성 호환
- PostgreSQL > MongoDB: ACID 필수

## 미해결 사항
- 토큰 갱신 전략

## 아키텍처 변경
- 인증 미들웨어 레이어 추가 (M3)

## 다음 단계
- 토큰 갱신 엔드포인트
```

**초기화 규칙**:
- M0 delta log 생성 직후 첫 번째 롤링 요약을 생성한다
- M0 → M1 사이에 롤링 요약이 없으면, M0 delta에서 자동 생성한다
- 세션 시작 시 이전 롤링 요약이 없는 경우: 존재하는 모든 delta log를 시간순으로 병합하여 요약을 재구성한다

**갱신 규칙**:
- 마일스톤 완료 시 갱신 (delta log 생성과 동시)
- 컨텍스트 잘림(compaction) 발생 시에도 갱신
- 잘린 구간만 요약하여 기존 롤링 요약에 병합
- 새 요약이 기존 섹션과 충돌 시, 새 요약이 우선

### 3.3 변경 감지 (점진적 구현)

초기에는 단순한 파일 해시 비교로 시작하고, 필요에 따라 Merkle Tree로 확장.

**최소 구현**:
```
1. 마일스톤 시작 시 파일 해시 스냅샷 저장
2. 마일스톤 완료 시 새 스냅샷과 비교
3. 변경된 파일만 델타 엔트리에 기록
```

**확장 구현** (필요 시):
- Merkle Tree 기반 O(log n) 변경 감지
- 콘텐츠 해시 → 요약 캐싱
- AST 기반 함수 수준 변경 추적

## 작업 항목

### 3.1 델타 로그
- [x] 델타 엔트리 JSON 스키마 확정 → `delta-schema.json`
- [x] 결정론적 병합 규칙 문서화 → `merge-rules.md`
- [x] 병합 규칙의 엣지 케이스 정의 (충돌, 모호함) → `merge-rules.md`
- [x] 델타 로그 → 컨텍스트 주입 포맷 정의 → `context-injection.md`

### 3.2 롤링 요약
- [x] 강제 섹션 목록 확정 → `rolling-summary-template.md`
- [x] 요약 생성 트리거 조건 정의 → `rolling-summary-template.md`
- [x] 요약 품질 검증 방법 (정보 손실 감지) → `rolling-summary-template.md`
- [x] 최대 요약 크기 (토큰) 정의 → `rolling-summary-template.md`

### 3.3 변경 감지
- [x] 최소 구현 (파일 해시 비교) 설계 → `change-detection.md`
- [x] 확장 구현 (Merkle Tree) 설계 (Phase 3 이후) → `change-detection.md`

## 선행 조건

- Phase 1의 프로세스 모델 (마일스톤 구조가 델타 생성 시점을 결정)

## 완료 기준

- [ ] 10+ 마일스톤 작업에서 토큰 소비 측정
- [ ] 누적 컨텍스트 없이 작업한 경우와 비교하여 품질 차이 관찰
- [ ] 델타 로그에서 정보 손실이 발생하지 않음을 확인

## 기술 참조

상세 자료구조/알고리즘: [../docs/references/context-management.md](../../docs/references/context-management.md)
