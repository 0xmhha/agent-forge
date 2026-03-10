# 컨텍스트 주입 전략

## 개요

누적된 컨텍스트를 새 에이전트 세션에 효율적으로 주입하는 방법을 정의한다. 핵심은 "필요한 정보만, 적절한 양만, 올바른 형식으로" 전달하는 것이다.

**목표**:
- 에이전트가 이전 마일스톤의 맥락을 이해하고 연속적으로 작업 가능
- 토큰 예산 내에서 최대한의 정보 전달
- 프로젝트 규모가 커져도 주입 비용이 선형 이하로 유지

---

## 주입 시점

### 마일스톤 시작 시 자동 주입

새 마일스톤이 시작될 때 아래 정보가 시스템 프롬프트 또는 초기 메시지에 주입된다:

```
[마일스톤 N+1 시작]
    │
    ▼
[누적 컨텍스트 로드]
    ├── accumulated.json (결정론적 병합 결과)
    ├── rolling-summary (최신 롤링 요약)
    └── 현재 마일스톤 계획
    │
    ▼
[토큰 예산 내 압축]
    │
    ▼
[구조화된 마크다운으로 포맷팅]
    │
    ▼
[에이전트 세션에 주입]
```

### 세션 중간 주입 (On-demand)

에이전트가 작업 중 추가 컨텍스트가 필요한 경우:
- 이전 마일스톤의 특정 결정 배경 조회
- 특정 파일의 변경 이력 조회
- 미해결 사항의 상세 내용 조회

이 경우 **요약 레벨에서 시작하여 필요 시 상세로 확장**한다 (Progressive Detail).

---

## 주입 형식

주입되는 컨텍스트는 **구조화된 마크다운**으로 포맷팅한다. 에이전트가 파싱하기 쉽고, 사람이 읽기에도 명확한 형식이다.

### 마크다운 구조

```markdown
# 프로젝트 누적 컨텍스트 (M{N-1}까지)

> 이 컨텍스트는 이전 마일스톤의 결정, 변경사항, 미해결 이슈를 요약한 것입니다.
> 상세 정보가 필요하면 요청하세요.

## 핵심 결정 [30%]
{결정 목록}

## 수정된 파일 [25%]
{파일 변경 요약}

## 미해결 사항 [20%]
{미해결 이슈 목록}

## 아키텍처 변경 [15%]
{구조적 변경사항}

## 다음 단계 [10%]
{현재 마일스톤의 작업 목록}
```

---

## 토큰 예산 할당

### 기본 예산: 총 3,000 토큰

전체 컨텍스트 윈도우(128K)의 약 2.3%를 누적 컨텍스트에 할당한다. 나머지는 현재 작업 컨텍스트, 도구 출력, 대화 이력에 사용.

| 섹션 | 비율 | 토큰 | 근거 |
|------|------|------|------|
| 핵심 결정 | 30% | ~900 | 결정이 가장 중요. 잘못된 결정을 반복하면 전체 재작업 |
| 수정된 파일 | 25% | ~750 | 현재 코드 상태를 파악하기 위한 최소 정보 |
| 미해결 사항 | 20% | ~600 | 놓치면 안 되는 활성 이슈. 현재 작업과의 관련성 높음 |
| 아키텍처 변경 | 15% | ~450 | 전체 구조 이해를 위한 최소한의 정보 |
| 다음 단계 | 10% | ~300 | 현재 마일스톤의 즉각적 작업 방향 |

### 프로젝트 규모별 조정

| 마일스톤 수 | 총 예산 | 결정 | 파일 | 미해결 | 아키텍처 | 다음 |
|------------|---------|------|------|--------|---------|------|
| 1-5 | 1,500 | 450 | 375 | 300 | 225 | 150 |
| 6-12 | 3,000 | 900 | 750 | 600 | 450 | 300 |
| 13-20 | 4,000 | 1,200 | 1,000 | 800 | 600 | 400 |
| 20+ | 5,000 | 1,500 | 1,250 | 1,000 | 750 | 500 |

---

## Progressive Detail (점진적 상세화)

### 3단계 상세 수준

모든 섹션은 3단계 상세 수준을 가진다. 기본적으로 Level 1(요약)만 주입되고, 에이전트가 필요 시 하위 레벨을 요청할 수 있다.

**Level 1 — 요약 (기본 주입)**:
```markdown
## 핵심 결정
- JWT 인증 (M3) | PostgreSQL (M1) | Stripe 결제 (M5) | Redis 캐싱 (M4)
총 8개 결정. 상세 내역은 `[결정 상세]`를 요청하세요.
```

**Level 2 — 상세**:
```markdown
## 핵심 결정
- JWT > 세션: 무상태 우선, 수평 확장 (M3)
- PostgreSQL > MongoDB: ACID 보장, 트랜잭션 결제 (M1)
- Stripe > 자체 결제: PCI DSS 위임, MVP 속도 (M5)
- Redis > 인메모리: Rate limit, 서버 재시작 시 유지 (M4)
- RS256 > HS256: 비대칭 키, 마이크로서비스 대비 (M3)
- bcrypt > argon2: 기존 의존성 호환 (M2)
- FastAPI > Flask: 비동기, 자동 OpenAPI (M1)
- SQLAlchemy > raw SQL: ORM 생산성 (M1)
```

**Level 3 — 전체 (원본 델타 엔트리)**:
```markdown
## 핵심 결정

### M1: 프로젝트 초기 설정
- **FastAPI > Flask**: 비동기 네이티브 지원, 자동 OpenAPI 문서 생성, Pydantic 통합
  - 기각: Flask (동기 기본, 확장 패키지 필요), Django (과도한 규모)
- **PostgreSQL > MongoDB**: ACID 트랜잭션 필수 (결제 로직), 관계형 데이터 모델 적합
  - 기각: MongoDB (트랜잭션 제한), SQLite (동시 접속 제한)
...
```

### 상세화 요청 프로토콜

에이전트가 상세 정보를 요청하는 형식:

```
[상세 요청] 섹션: 핵심 결정, 레벨: 2
[상세 요청] 섹션: 수정된 파일, 필터: src/auth/*, 레벨: 3
[상세 요청] 섹션: 미해결 사항, 태그: [긴급], 레벨: 2
```

---

## 실전 예시: 마일스톤 8 시작 시 주입 컨텍스트

아래는 12개 마일스톤 프로젝트(E-커머스 백엔드)의 M8 시작 시 주입되는 컨텍스트이다.

```markdown
# 프로젝트 누적 컨텍스트 (M7까지)

> E-커머스 백엔드 API. FastAPI + PostgreSQL + Redis.
> 총 파일 62개, 라인 5,840. 핵심 모듈: auth, api, models, services, middleware.
> 이 요약은 M1-M7의 델타 로그를 병합한 결과입니다.

## 핵심 결정 (12개)

- FastAPI > Flask: 비동기 네이티브, 자동 OpenAPI 문서 (M1)
- PostgreSQL > MongoDB: ACID 필수, 결제 트랜잭션 (M1)
- SQLAlchemy > raw SQL: ORM 생산성, Alembic 마이그레이션 (M1)
- bcrypt > argon2: 기존 의존성 호환, 충분한 보안 수준 (M2)
- JWT > 세션: 무상태, 수평 확장 시 세션 스토어 불필요 (M3)
- RS256 > HS256: 비대칭 키, 서비스 간 토큰 검증 (M3)
- Redis > 인메모리: Rate limit + 캐싱, 서버 재시작 시 유지 (M4)
- Stripe > 자체 결제: PCI DSS 위임, 웹훅 기반 비동기 처리 (M5)
- Celery > asyncio 태스크: 장시간 작업 분리, 재시도 로직 내장 (M6)
- S3 > 로컬 파일: 상품 이미지 CDN 연동, 무제한 확장 (M6)
- ELK > 자체 로깅: 구조화 로그, 검색/대시보드 (M7)
- 이벤트 소싱 > 직접 상태 변경: 주문 상태 추적, 감사 로그 (M7)

## 수정된 파일 (최근 3개 마일스톤)

**M7** — 로깅 및 이벤트 시스템:
- src/events/order_events.py: 주문 이벤트 발행/구독, EventBus 패턴 (생성)
- src/events/event_store.py: 이벤트 저장소, PostgreSQL JSONB 활용 (생성)
- src/middleware/logging.py: 구조화 로깅 미들웨어, 요청 ID 추적 (생성)
- src/config.py: ELK 연결 설정, 로그 레벨 환경변수 추가 (수정)

**M6** — 비동기 작업 및 이미지 처리:
- src/tasks/celery_app.py: Celery 앱 설정, Redis 브로커 (생성)
- src/tasks/image_processing.py: 상품 이미지 리사이즈/최적화 태스크 (생성)
- src/services/s3_client.py: S3 업로드/다운로드, presigned URL 생성 (생성)
- src/api/products.py: 이미지 업로드 엔드포인트 추가 (수정)

**M5** — 결제 시스템:
- src/api/payments.py: 결제 API, Stripe 웹훅 처리 (생성)
- src/services/stripe_client.py: Stripe SDK 래퍼, 멱등성 키 (생성)

## 미해결 사항 (4개)

- RBAC 세부 권한 모델 미정의 (M3) [장기]
- 환불 자동화 로직 미구현 — 현재 수동 처리 (M5) [긴급]
- Celery 워커 모니터링/알림 미설정 (M6)
- 이벤트 스토어 스냅샷 전략 미정의 — 이벤트 누적 시 조회 성능 (M7)

## 아키텍처 변경

- 프로젝트 초기 구조: FastAPI + PostgreSQL + SQLAlchemy (M1)
- 인증 미들웨어 레이어: 데코레이터 기반 라우트 보호 (M3)
- Redis 의존성: Rate limiting, 세션 캐싱, Celery 브로커 (M4)
- Stripe 외부 연동: 웹훅 수신, 멱등성 보장 (M5)
- Celery 비동기 레이어: 이미지 처리, 이메일 발송 (M6)
- S3 파일 스토리지: 상품 이미지, presigned URL (M6)
- 이벤트 소싱: 주문 상태 추적, EventBus 패턴 (M7)
- ELK 로깅 파이프라인: 구조화 로그, 요청 추적 (M7)

## 다음 단계 (M8: 검색 및 추천)

- 상품 검색 엔진 구현 (Elasticsearch 연동)
- 검색 자동완성 API
- 최근 본 상품 기반 추천 로직
- 검색 결과 필터링 (가격, 카테고리, 평점)
- 환불 자동화 로직 구현 (M5 미해결 사항 해소)
```

---

## 주입 알고리즘

```python
def prepare_injection(
    accumulated: dict,
    current_milestone: str,
    milestone_plan: str,
    token_budget: int = 3000
) -> str:
    """누적 컨텍스트를 주입 가능한 마크다운으로 변환한다.

    Args:
        accumulated: 누적 컨텍스트 (결정론적 병합 결과)
        current_milestone: 현재 마일스톤 식별자
        milestone_plan: 현재 마일스톤 계획 텍스트
        token_budget: 총 토큰 예산

    Returns:
        구조화된 마크다운 문자열
    """
    # 1. 섹션별 예산 할당
    budgets = {
        "decisions": int(token_budget * 0.30),
        "files": int(token_budget * 0.25),
        "unresolved": int(token_budget * 0.20),
        "architecture": int(token_budget * 0.15),
        "next_steps": int(token_budget * 0.10),
    }

    # 2. 각 섹션을 예산 내에서 포맷팅
    sections = {
        "decisions": format_decisions(accumulated["decisions"], budgets["decisions"]),
        "files": format_files(accumulated["files_changed"], budgets["files"]),
        "unresolved": format_unresolved(accumulated["unresolved"], budgets["unresolved"]),
        "architecture": extract_architecture(accumulated, budgets["architecture"]),
        "next_steps": format_next_steps(accumulated["next_steps"], milestone_plan, budgets["next_steps"]),
    }

    # 3. 예산 재분배 (특정 섹션이 예산 미만이면 다른 섹션에 할당)
    sections = redistribute_budget(sections, budgets, token_budget)

    # 4. 마크다운 조립
    snapshot = accumulated.get("context_snapshot", {})
    header = build_header(current_milestone, snapshot)

    return assemble_markdown(header, sections)


def redistribute_budget(sections: dict, budgets: dict, total: int) -> dict:
    """사용하지 않은 예산을 다른 섹션에 재분배한다.
    결정 섹션에 우선 할당."""
    unused = 0

    for key, budget in budgets.items():
        actual = estimate_tokens(sections[key])
        if actual < budget:
            unused += (budget - actual)

    if unused > 0:
        # 결정 > 미해결 > 파일 > 아키텍처 > 다음 순서로 재분배
        priority = ["decisions", "unresolved", "files", "architecture", "next_steps"]
        for key in priority:
            if unused <= 0:
                break
            expanded = expand_section(sections[key], unused)
            used = estimate_tokens(expanded) - estimate_tokens(sections[key])
            sections[key] = expanded
            unused -= used

    return sections
```

---

## 주입 시 주의사항

### 하지 말 것

1. **전체 파일 내용 주입 금지**: 파일 경로 + 요약만 주입. 파일 내용은 에이전트가 필요 시 직접 조회
2. **오래된 next_steps 주입 금지**: 현재 마일스톤과 무관한 과거 작업 목록은 노이즈
3. **중복 정보 주입 금지**: 같은 결정이 "결정" 섹션과 "아키텍처" 섹션에 중복되지 않도록
4. **LLM으로 요약해서 주입 금지**: 누적 컨텍스트는 결정론적으로 생성된 그대로 주입. 주입 시점에서의 추가 요약은 정보 손실 위험

### 해야 할 것

1. **컨텍스트 출처 명시**: 각 항목에 마일스톤 번호를 표기하여 "언제 결정/변경됐는지" 추적 가능하게
2. **상세 조회 경로 안내**: 에이전트가 더 깊은 정보를 원할 때 어떻게 접근하는지 안내
3. **현재 마일스톤 계획 포함**: 누적 컨텍스트만으로는 "지금 무엇을 해야 하는지" 불명확
4. **프로젝트 스냅샷 포함**: 전체 파일 수, 라인 수, 핵심 모듈 목록으로 규모감 제공
