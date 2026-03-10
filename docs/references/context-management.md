# 컨텍스트 관리 기술 레퍼런스

누적 코드의 토큰 효율적 관리를 위한 자료구조, 알고리즘, 방법론 정리.

---

## 1. 자료구조

### 1.1 Merkle Tree (변경 감지)

파일 해시를 리프 노드로 하는 이진 트리. 루트 해시만 비교하면 변경 여부를 O(log n)으로 판정.

```
        [root hash]
       /           \
   [hash-AB]     [hash-CD]
   /      \      /      \
[hash-A] [hash-B] [hash-C] [hash-D]
   |        |        |        |
 file1    file2    file3    file4
```

- **사용 사례**: Cursor의 코드베이스 인덱싱
- **복잡도**: O(log n) 변경 감지, 변경된 브랜치만 탐색
- **효과**: 50,000 파일 기준 ~3.2MB/업데이트 → 변경 브랜치만으로 축소
- **적용**: 매 마일스톤 완료 시 트리 갱신, 변경 파일만 재요약

### 1.2 Call Graph + 위상 정렬 (의미 전파)

LSP로 호출 그래프를 구축하고, 위상 정렬 후 리프 함수부터 요약. 각 함수의 요약에 호출하는 함수의 요약을 포함.

```
main() ──→ processOrder() ──→ validatePayment()
                │                    │
                ▼                    ▼
          calculateTax()      chargeCard()
```

- **출처**: Code-Craft (arXiv:2504.08975)
- **복잡도**: O(V + E) 위상 정렬
- **효과**: 고립 임베딩 대비 82% 검색 정확도 향상 (7,531 함수, 5개 코드베이스)
- **적용**: 변경된 함수의 요약만 갱신, 상위 함수로 자동 전파

### 1.3 LSH / MinHash (중복 감지)

유사한 항목을 같은 해시 버킷에 매핑. 컨텍스트에 유사 내용이 이미 있는지 O(1)로 확인.

- **용도**: 중복 컨텍스트 삽입 방지, 근사 최근접 이웃 검색
- **복잡도**: O(1) 쿼리, O(n) 빌드
- **적용**: 코드 청크를 컨텍스트에 추가하기 전 중복 체크

### 1.4 MemTree (동적 트리 메모리)

각 노드가 텍스트 + 시맨틱 임베딩을 보유하는 동적 트리.

- 유사 노드 존재 → 병합
- 새 주제 → 새 브랜치 생성
- 오래된 정보 → 가지치기
- **출처**: OpenReview (MemTree: Dynamic Tree Memory for LLMs)
- **적용**: 프로젝트 지식의 장기 메모리 구조

---

## 2. 알고리즘

### 2.1 ACE (Agentic Context Engineering)

증분 컨텍스트 갱신 프레임워크 (arXiv:2510.04618, 2026-01 업데이트).

```
Generator → 작업 수행
    │ 결과
Reflector → 교훈 추출 (delta entries)
    │ 증분 항목
Curator → 구조화 병합 (결정론적, LLM 호출 없음)
    │ 갱신된 컨텍스트
Generator → 다음 작업
```

핵심 설계:
- **Delta entries**: 전체 재작성이 아닌 증분 불릿 포인트
- **결정론적 병합**: LLM으로 병합 시 환각 복리 누적 (context collapse). 규칙 기반 병합
- **항목화 구조**: 관련 항목만 국소적 업데이트
- **결과**: 에이전트 작업 +10.6%, 금융 벤치마크 +8.6%

### 2.2 Meta-RAG (계층적 검색)

다단계 좁히기로 대규모 코드베이스에서 관련 코드만 검색.

```
전체 (10,000 파일) → 파일 요약 제시 → 단축 목록 (50-100)
  → 함수 요약 제시 → 관련 함수 (10-20) → 전체 코드 검색
```

- **출처**: arXiv:2508.02611
- **효과**: 79.8% 코드베이스 압축, 파일 정확도 84.67%

### 2.3 ACON (적응적 관찰 압축)

Tool output(관찰)을 선택적으로 압축. 추론 체인은 보존, 도구 출력은 압축.

- **효과**: 26-54% 토큰 절감, SWE-bench 기준 품질 유지
- **핵심**: 추론 과정 > 원시 도구 데이터

### 2.4 Factory.ai 구조적 롤링 요약

대화 기록이 잘릴 때 잘린 부분만 요약하여 기존 롤링 요약에 병합.

```
[기존 롤링 요약] + [잘린 구간 요약] → [갱신된 롤링 요약]

구조적 섹션 강제:
- ## 수정된 파일
- ## 내린 결정
- ## 다음 단계
```

- **효과**: 36,000+ 메시지 테스트, Anthropic 기본 3.44 → 3.70
- **핵심**: 강제 섹션으로 "세부사항 조용히 사라짐" 방지

### 2.5 Verbatim Compaction (Morph)

LLM 요약 대신, 원본 텍스트를 규칙 기반으로 압축.

| 전략 | 압축률 | 정확도 | 환각 위험 |
|------|--------|--------|----------|
| LLM 요약 | 70-90% | 손실 | 중간 |
| Verbatim Compaction | 50-70% | 98% | 없음 |

- **적용**: 도구 출력, 에러 로그 등 정확성이 중요한 텍스트

---

## 3. 복합 아키텍처

5개 레이어를 결합한 최적 구성:

```
┌─────────────────────────────────────────────┐
│ Layer 5: 세션 관리                            │
│ - 구조적 롤링 요약 (Factory.ai)              │
│ - 관찰 마스킹 (ACON)                         │
│ - 잘린 구간만 증분 요약                       │
├─────────────────────────────────────────────┤
│ Layer 4: 컨텍스트 구성                        │
│ - ACE 델타 엔트리 (증분 갱신)                 │
│ - 결정론적 병합 (LLM 호출 없음)              │
│ - 구조적 섹션 강제                            │
├─────────────────────────────────────────────┤
│ Layer 3: 검색                                │
│ - Meta-RAG 점진적 좁히기                     │
│ - LSH 중복 제거                              │
│ - SEM-RAG 아키텍처 인식                      │
├─────────────────────────────────────────────┤
│ Layer 2: 코드 이해                            │
│ - AST 기반 청킹 (Tree-sitter)                │
│ - 호출 그래프 + 위상 정렬                     │
│ - 계층적 요약 (함수→파일→패키지→저장소)      │
├─────────────────────────────────────────────┤
│ Layer 1: 변경 감지                            │
│ - Merkle 트리 (파일 해시)                    │
│ - 변경된 파일만 재처리                        │
│ - 콘텐츠 해시 기반 캐싱                       │
└─────────────────────────────────────────────┘
```

### 비용 프로필

| 레이어 | 연산 | LLM 호출 | 실행 시점 |
|--------|------|----------|----------|
| L1 변경 감지 | Merkle diff | 없음 | 매 쿼리 |
| L2 코드 이해 | AST + 요약 | 있음 (비쌈) | 변경 시에만 (오프라인) |
| L3 검색 | 임베딩 + LSH | 없음 | 매 쿼리 |
| L4 컨텍스트 구성 | 델타 병합 | 없음 | 마일스톤 완료 시 |
| L5 세션 관리 | 롤링 요약 | 있음 (중간) | 컨텍스트 잘림 시에만 |

---

## 4. 참고 문헌

- [ACE: Agentic Context Engineering](https://arxiv.org/abs/2510.04618)
- [Code-Craft: Hierarchical Graph-Based Code Summarization](https://arxiv.org/html/2504.08975v1)
- [Meta-RAG on Large Codebases](https://arxiv.org/html/2508.02611v1)
- [Hierarchical Repository-Level Code Summarization](https://arxiv.org/html/2501.07857v1)
- [ACON: Optimizing Context Compression](https://openreview.net/pdf?id=7JbSwX6bNL)
- [Compressing Context - Factory.ai](https://factory.ai/news/compressing-context)
- [How Cursor Indexes Codebases](https://read.engineerscodex.com/p/how-cursor-indexes-codebases-fast)
- [SEM-RAG - Tabnine](https://www.tabnine.com/blog/enhancing-ai-coding-assistants-with-context-using-rag-and-sem-rag/)
- [MemTree: Dynamic Tree Memory](https://openreview.net/forum?id=moXtEmCleY)
- [Compaction vs Summarization - Morph](https://www.morphllm.com/compaction-vs-summarization)
- [Prompt Compression Survey (NAACL 2025)](https://github.com/ZongqianLi/Prompt-Compression-Survey)
- [Reducing Token Usage of SE Agents (TU Wien)](https://repositum.tuwien.at/bitstream/20.500.12708/224666/1/Hrubec%20Nicolas%20-%202025%20-%20Reducing%20Token%20Usage%20of%20Software%20Engineering%20Agents.pdf)
