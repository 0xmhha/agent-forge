# 방법론 적용 관찰: M6 (2026-03-12)

## 적용 대상

- **Phase 1**: Complexity assessment → Standard tier, QR gate 1회
- **Phase 2**: domain-profile.yaml의 forbidden/required 패턴으로 QR 검사 기준 구성
- **Phase 3**: Delta log (M6-handler-wiring.json) + Rolling summary 생성
- **Phase 4**: Session metrics (2026-03-12-m6-handler-wiring.json) 생성

---

## 관찰 결과

### Phase 1: Process Model

#### 잘 동작한 것
- **Complexity assessment 자동 판정**: 파일 8개 → Standard 판정이 적절했음
- **QR 1회 MUST+SHOULD**: 2개 SHOULD 발견 (action handler 에러 누락, sanitize 테스트 부재) — 둘 다 유의미
- **이중 경로 검증**: `_make_action_handler`의 에러 누락은 "문제인 이유"가 명확 (token leak 가능성)

#### 개선 필요
- **QR 실행 시점 불명확**: "QR 1회"가 모든 작업 완료 후인지, 각 sub-step 후인지 모호. M6은 6개 sub-step이 있었는데 전체 완료 후 1회 실행함. 중간에 발견했으면 더 일찍 수정 가능
- **QR 출력 형식의 위치 미정의**: QR 결과를 어디에 기록하는지 규정 없음. 델타 로그? 별도 파일? 롤링 요약? → 현재는 델타 로그의 lessons에 흡수
- **Tier 전환 규칙 테스트 안 됨**: M6은 예상대로 Standard였지만, 실제로 "작업 중 복잡도 상승"이 발생하는 케이스를 아직 경험하지 못함

### Phase 2: Domain Profiles

#### 잘 동작한 것
- **forbidden_patterns가 QR 검사 체크리스트로 유용**: `token_in_response`, `token_in_error_message` 패턴이 구체적이어서 검사가 기계적으로 가능
- **required_patterns가 누락 감지에 효과적**: `error_handling` 패턴으로 `_make_action_handler`의 try/except 누락 발견

#### 개선 필요
- **detection_hint와 실제 검사 방법 간 갭**: `detection_hint: "ghp_, gho_..."` 라고 했지만 실제로는 grep으로 ToolResult 반환 지점을 전수 검사함. detection_hint가 "어떻게 검사하는지"를 더 구체적으로 서술해야 함
- **severity와 QR 판정 매핑 불명확**: domain-profile의 MUST/SHOULD가 Phase 1 QR의 MUST/SHOULD와 동일한 의미인지 명시되지 않음. 현재는 동일하게 취급했지만, Phase 1 문서에는 domain-profile 연계 규칙이 없음
- **priority_matrix 미활용**: safety=0.7, maintainability=0.8 같은 숫자가 QR 판정에 어떻게 반영되는지 정의 없음. 현재 session에서 전혀 참조하지 않음

### Phase 3: Context Management

#### 잘 동작한 것
- **Delta log 스키마가 구조화된 기록 강제**: files_changed, decisions, lessons, unresolved, next_steps의 구분이 "무엇을 기록해야 하는지" 명확
- **Rolling summary 5개 강제 섹션**: 작성 시 "빠뜨린 것이 없는지" 체크리스트로 기능

#### 개선 필요
- **M0 delta log의 "baseline" 역할 불명확**: M0은 프로젝트 전체 기록인데, delta-schema는 "마일스톤 완료 시 증분"을 가정. M0이 예외적 케이스라는 것이 스키마에 표현되지 않음
- **Rolling summary 갱신 트리거**: "마일스톤 완료 시" 갱신이라 했는데, M0→M6 사이(M1-M5)에는 롤링 요약 없이 진행됨. 실제로는 세션 시작 시 이전 롤링 요약을 읽어야 하는데, 없으면 M0부터 재구성해야 함
- **context_snapshot의 가치 불분명**: total_files=29, total_lines=2065를 기록했지만, 이것을 어디서 어떻게 활용하는지 분석 플레이북에 정의 없음
- **Delta log 파일명 컨벤션 없음**: M0-baseline.json, M6-handler-wiring.json으로 했지만 이름 규칙이 정의되지 않음

### Phase 4: Measurement

#### 잘 동작한 것
- **세션 로그 스키마가 수집 항목 명확화**: 뭘 기록해야 하는지 고민할 필요 없음
- **rework_count 정의가 명확**: "같은 파일 2회 이상 수정" — test 파일 2개가 해당

#### 개선 필요
- **토큰 수집 불가**: `tokens.total=0`으로 기록함. ccusage 같은 외부 도구 필요한데, 세션 중에는 알 수 없음. Phase 4 가이드에 "세션 종료 후 수집"이라 했지만, 실제로 이 값을 채우러 돌아오는 워크플로우가 없음
- **duration_minutes 수집 불가**: 세션 시작/종료 시각을 자동 추적하는 메커니즘 없음. 특히 컨텍스트 압축(compaction)으로 세션이 이어지면 경계가 모호
- **파생 메트릭 계산 시점 미정의**: "토큰/파일" 같은 파생 메트릭을 언제 계산하는지 워크플로우에 없음
- **첫 번째 실제 세션인데 비교 기준선 없음**: 메트릭의 가치는 비교에 있는데, 단일 데이터 포인트로는 의미 없음. "n회 축적 후 분석" 같은 가이드 필요

---

## 종합 개선 제안

| # | Phase | 개선 사항 | 우선순위 |
|---|-------|----------|---------|
| 1 | P1 | QR 실행 시점 명시: Standard는 "모든 코드 변경 완료 후, 커밋 전" | 높음 |
| 2 | P1×P2 | domain-profile의 forbidden/required → QR 체크리스트 자동 생성 규칙 추가 | 높음 |
| 3 | P2 | priority_matrix의 구체적 활용 규칙 정의 (또는 삭제) | 중간 |
| 4 | P2 | detection_hint → detection_method로 변경, 검사 방법 구체화 | 중간 |
| 5 | P3 | Delta log 파일명 컨벤션: `M{N}-{slug}.json` 형식 명시 | 낮음 |
| 6 | P3 | M0 baseline 엔트리 역할 별도 정의 (스키마의 description에 추가) | 낮음 |
| 7 | P3 | Rolling summary 초기화 규칙: M0 delta로부터 첫 요약 생성 시점 명시 | 중간 |
| 8 | P4 | 토큰 수집 워크플로우: "세션 종료 → ccusage → 세션 로그 갱신" 절차 명시 | 높음 |
| 9 | P4 | 최소 데이터 포인트 수 명시: "5개 세션 축적 후 파생 메트릭 분석 시작" | 중간 |
| 10 | P1×P3 | QR 결과 기록 위치: delta log의 별도 필드 (예: qr_result) 추가 | 중간 |
