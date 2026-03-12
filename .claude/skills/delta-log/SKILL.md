---
name: delta-log
description: |
  마일스톤 완료 시 delta-log 엔트리를 생성하고 rolling-summary를 갱신한다.
  /delta-log로 수동 호출 또는 /milestone에서 자동 호출.
trigger-keywords: delta, 델타, log, 기록
user-invocable: true
---

## Instructions

### Step 1: 변경 사항 수집

```bash
!`cd /Users/wm-it-22-00661/Work/github/study/ai/agent-forge && git diff --stat HEAD~1`
```

### Step 2: 마일스톤 번호 결정

기존 delta-log에서 마지막 마일스톤 번호를 확인:

```bash
!`ls delta-logs/M*.json 2>/dev/null | sort -V | tail -1`
```

다음 번호를 사용한다 (예: M6이 마지막이면 M7).

### Step 3: delta-log 엔트리 생성

`delta-logs/M{N}-{slug}.json` 파일을 생성한다.

스키마 (`phases/phase-3-context-management/delta-schema.json`) 준수:

```json
{
  "milestone": "M{N}",
  "timestamp": "{ISO 8601 UTC}",
  "files_changed": [
    {"path": "relative/path", "action": "created|modified|deleted", "summary": "무엇을 왜 (200자)"}
  ],
  "decisions": [
    {"decision": "선택 A > B", "rationale": "근거", "alternatives_rejected": ["기각된 대안"]}
  ],
  "qr_result": {
    "verdict": "PASS|PASS_WITH_CONCERNS|NEEDS_CHANGES",
    "iteration": 1,
    "findings": [
      {"category": "CATEGORY", "severity": "MUST|SHOULD|COULD", "summary": "요약", "resolved": true}
    ]
  },
  "lessons": ["이 마일스톤에서 얻은 교훈"],
  "unresolved": ["아직 해결되지 않은 이슈"],
  "next_steps": ["다음에 할 작업"],
  "context_snapshot": {
    "total_files": 0,
    "total_lines": 0,
    "key_modules": []
  }
}
```

### Step 4: context_snapshot 수집

```bash
!`find tools/ phases/ -name "*.py" -o -name "*.md" -o -name "*.json" -o -name "*.yaml" | grep -v __pycache__ | grep -v .venv | grep -v node_modules | wc -l`
```

```bash
!`find tools/ phases/ -name "*.py" -o -name "*.md" | grep -v __pycache__ | grep -v .venv | xargs wc -l 2>/dev/null | tail -1`
```

### Step 5: rolling-summary 갱신

`delta-logs/rolling-summary.md`를 갱신한다.
5개 필수 섹션: 수정된 파일, 핵심 결정, 미해결 사항, 아키텍처 변경, 다음 단계.

이전 delta-log의 `unresolved`에서 해결된 항목은 제거.
이전 `next_steps`에서 완료된 항목은 제거.

### Step 6: 완료 확인

생성된 파일 경로를 보고한다.
