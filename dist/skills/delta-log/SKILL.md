---
name: delta-log
description: |
  마일스톤 완료 시 delta-log 엔트리(M{N}-{slug}.json)를 생성하고 rolling-summary를 갱신한다.
  작업 완료 후 컨텍스트를 구조적으로 기록하여 다음 세션에서 활용한다.
  /milestone 워크플로우의 일부로 자동 호출되거나, 독립적으로 수동 호출 가능.
trigger-keywords: delta, 델타, log, 기록, delta-log
user-invocable: true
---

## Instructions

### Step 1: 변경 사항 수집

```bash
!`git diff --stat HEAD~1 2>/dev/null || git show --stat HEAD 2>/dev/null || echo "no commits yet"`
```

### Step 2: 마일스톤 번호 결정

프로젝트의 delta-logs 디렉토리에서 마지막 번호 확인:

```bash
!`ls delta-logs/M*.json 2>/dev/null | sort -V | tail -1 || echo "no existing delta-logs"`
```

디렉토리가 없으면 생성하고 M0부터 시작:

```bash
!`mkdir -p delta-logs`
```

### Step 3: delta-log 엔트리 생성

`delta-logs/M{N}-{slug}.json` 파일을 생성한다.

필수 필드:

```json
{
  "milestone": "M{N}",
  "timestamp": "{ISO 8601 UTC}",
  "files_changed": [
    {"path": "relative/path", "action": "created|modified|deleted", "summary": "무엇을 왜"}
  ],
  "decisions": [
    {"decision": "선택 A > B", "rationale": "근거", "alternatives_rejected": ["기각된 대안"]}
  ],
  "qr_result": {
    "verdict": "PASS|PASS_WITH_CONCERNS|NEEDS_CHANGES",
    "iteration": 1,
    "findings": []
  },
  "lessons": [],
  "unresolved": [],
  "next_steps": [],
  "context_snapshot": {
    "total_files": 0,
    "total_lines": 0,
    "key_modules": []
  }
}
```

### Step 4: context_snapshot 수집

프로젝트의 소스 파일 수와 라인 수를 자동 수집:

```bash
!`find . -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.go" | grep -v node_modules | grep -v .venv | grep -v __pycache__ | wc -l`
```

### Step 5: rolling-summary 갱신

`delta-logs/rolling-summary.md`를 갱신한다.
5개 필수 섹션:
1. **수정된 파일** — 현재까지 변경된 주요 파일과 마일스톤
2. **핵심 결정** — 모든 결정 누적 (삭제 금지)
3. **미해결 사항** — 해결된 항목 제거, 새 항목 추가
4. **아키텍처 변경** — 구조적 변경 기록
5. **다음 단계** — 완료 항목 제거, 새 항목 추가

### Step 6: 완료 보고

생성/갱신된 파일 경로를 보고한다.
