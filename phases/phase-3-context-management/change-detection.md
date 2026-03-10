# 변경 감지 전략

## 개요

변경 감지는 컨텍스트 관리의 첫 번째 단계이다. 마일스톤 사이에 "무엇이 변경됐는가"를 정확하고 효율적으로 판별하여, 변경된 파일만 델타 엔트리에 기록한다.

두 가지 구현 수준을 제공한다:
1. **최소 구현**: 파일 해시 비교 (SHA-256) — 즉시 사용 가능
2. **확장 구현**: Merkle Tree — 대규모 프로젝트용 (Phase 3 이후)

---

## 최소 구현: 파일 해시 비교

### 원리

각 파일의 내용을 SHA-256으로 해시하여 스냅샷을 생성한다. 두 스냅샷을 비교하면 변경/추가/삭제된 파일을 O(n)에 판별할 수 있다.

### 스냅샷 형식

```json
{
  "milestone": "M3",
  "timestamp": "2026-03-10T15:30:00Z",
  "algorithm": "sha256",
  "files": {
    "src/auth/jwt.py": "a1b2c3d4e5f6...",
    "src/models/user.py": "f6e5d4c3b2a1...",
    "src/config.py": "1a2b3c4d5e6f...",
    "tests/test_auth.py": "6f5e4d3c2b1a..."
  },
  "excluded_patterns": [
    "node_modules/**",
    ".git/**",
    "__pycache__/**",
    "*.pyc",
    ".env",
    "*.lock"
  ]
}
```

### 비교 알고리즘

```python
def compare_snapshots(before: dict, after: dict) -> dict:
    """두 스냅샷을 비교하여 변경 목록을 반환한다.

    Args:
        before: 마일스톤 시작 시 스냅샷
        after: 마일스톤 완료 시 스냅샷

    Returns:
        {created: [...], modified: [...], deleted: [...]}
    """
    before_files = before["files"]
    after_files = after["files"]

    before_paths = set(before_files.keys())
    after_paths = set(after_files.keys())

    created = []
    modified = []
    deleted = []

    # 새로 생성된 파일
    for path in (after_paths - before_paths):
        created.append({
            "path": path,
            "action": "created",
            "hash": after_files[path]
        })

    # 삭제된 파일
    for path in (before_paths - after_paths):
        deleted.append({
            "path": path,
            "action": "deleted",
            "hash": before_files[path]
        })

    # 변경된 파일 (양쪽에 존재하지만 해시가 다름)
    for path in (before_paths & after_paths):
        if before_files[path] != after_files[path]:
            modified.append({
                "path": path,
                "action": "modified",
                "hash_before": before_files[path],
                "hash_after": after_files[path]
            })

    return {
        "created": created,
        "modified": modified,
        "deleted": deleted,
        "unchanged_count": len(before_paths & after_paths) - len(modified)
    }
```

### 스냅샷 생성

```python
import hashlib
import os
from pathlib import Path
from fnmatch import fnmatch

EXCLUDED_PATTERNS = [
    "node_modules/**", ".git/**", "__pycache__/**",
    "*.pyc", ".env", "*.lock", "dist/**", "build/**"
]

def is_excluded(path: str, patterns: list[str]) -> bool:
    """경로가 제외 패턴에 매칭되는지 확인한다."""
    for pattern in patterns:
        if fnmatch(path, pattern):
            return True
    return False

def hash_file(file_path: str) -> str:
    """파일 내용의 SHA-256 해시를 반환한다."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def create_snapshot(project_root: str, milestone: str) -> dict:
    """프로젝트 전체 파일의 해시 스냅샷을 생성한다.

    Args:
        project_root: 프로젝트 루트 디렉터리
        milestone: 현재 마일스톤 식별자

    Returns:
        스냅샷 딕셔너리
    """
    files = {}
    root = Path(project_root)

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue

        relative = str(file_path.relative_to(root))

        if is_excluded(relative, EXCLUDED_PATTERNS):
            continue

        files[relative] = hash_file(str(file_path))

    return {
        "milestone": milestone,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "algorithm": "sha256",
        "files": files,
        "excluded_patterns": EXCLUDED_PATTERNS
    }
```

### 저장 전략

스냅샷은 프로젝트의 `.agent-forge/snapshots/` 디렉터리에 저장한다.

```
.agent-forge/
├── snapshots/
│   ├── M1.json      # M1 시작 시 스냅샷
│   ├── M1-end.json  # M1 완료 시 스냅샷
│   ├── M2.json
│   ├── M2-end.json
│   └── ...
├── deltas/
│   ├── M1.json      # M1 델타 엔트리
│   ├── M2.json
│   └── ...
└── accumulated.json  # 누적 컨텍스트
```

**보존 정책**: 최근 3개 마일스톤의 스냅샷만 유지. 그 이전은 델타 엔트리만으로 충분.

---

## 확장 구현: Merkle Tree (향후)

### 필요성

파일 수가 수천 개를 넘으면 전체 파일 해시 비교의 O(n) 비용이 부담될 수 있다. Merkle Tree를 사용하면 루트 해시만 비교하여 변경 여부를 즉시 판별하고, 변경된 브랜치만 탐색하여 O(log n)에 변경 파일을 찾을 수 있다.

### 트리 구조

```
프로젝트 루트
    │
    ├── src/                    hash: abc123
    │   ├── auth/               hash: def456
    │   │   ├── jwt.py          hash: 111aaa
    │   │   └── refresh.py      hash: 222bbb
    │   ├── api/                hash: ghi789
    │   │   ├── routes.py       hash: 333ccc
    │   │   └── payments.py     hash: 444ddd
    │   └── models/             hash: jkl012
    │       ├── user.py         hash: 555eee
    │       └── base.py         hash: 666fff
    └── tests/                  hash: mno345
        ├── test_auth.py        hash: 777ggg
        └── test_payments.py    hash: 888hhh
```

각 디렉터리 노드의 해시는 자식 노드 해시의 결합이다:
```
hash(directory) = SHA256(sorted(child_name + ":" + child_hash for child in children))
```

### 점진적 갱신 알고리즘

```python
class MerkleNode:
    def __init__(self, name: str, is_file: bool):
        self.name = name
        self.is_file = is_file
        self.hash = None
        self.children = {}  # name → MerkleNode

def update_file(tree: MerkleNode, file_path: str, new_hash: str) -> list[str]:
    """파일 하나가 변경됐을 때 트리를 갱신한다.
    변경된 파일에서 루트까지의 경로만 재계산한다.

    Args:
        tree: Merkle 트리 루트
        file_path: 변경된 파일의 상대 경로
        new_hash: 새 파일 해시

    Returns:
        재계산된 경로 목록 (디버깅용)
    """
    parts = file_path.split("/")
    recalculated = []

    # 리프 노드까지 탐색
    node = tree
    ancestors = [tree]

    for part in parts[:-1]:
        node = node.children[part]
        ancestors.append(node)

    # 리프 노드(파일) 해시 갱신
    file_name = parts[-1]
    node.children[file_name].hash = new_hash

    # 리프에서 루트까지 역방향 해시 재계산
    for ancestor in reversed(ancestors):
        old_hash = ancestor.hash
        ancestor.hash = compute_directory_hash(ancestor)
        recalculated.append(ancestor.name)

        if ancestor.hash == old_hash:
            break  # 해시가 같으면 상위 노드도 변경 없음

    return recalculated


def compute_directory_hash(node: MerkleNode) -> str:
    """디렉터리 노드의 해시를 자식 해시로부터 계산한다."""
    entries = sorted(
        f"{name}:{child.hash}"
        for name, child in node.children.items()
    )
    combined = "\n".join(entries)
    return hashlib.sha256(combined.encode()).hexdigest()
```

### 브랜치 전용 탐색

두 Merkle 트리를 비교할 때 해시가 다른 브랜치만 내려간다:

```python
def diff_trees(before: MerkleNode, after: MerkleNode, path: str = "") -> dict:
    """두 Merkle 트리를 비교하여 변경된 파일만 반환한다.
    해시가 같은 서브트리는 완전히 건너뛴다.

    Returns:
        {created: [...], modified: [...], deleted: [...]}
    """
    result = {"created": [], "modified": [], "deleted": []}

    # 루트 해시가 같으면 변경 없음
    if before.hash == after.hash:
        return result

    before_names = set(before.children.keys())
    after_names = set(after.children.keys())

    # 새로 생성된 노드
    for name in (after_names - before_names):
        full_path = f"{path}/{name}" if path else name
        child = after.children[name]
        if child.is_file:
            result["created"].append(full_path)
        else:
            # 디렉터리 전체가 새로 생성됨 — 모든 파일을 created로
            result["created"].extend(collect_all_files(child, full_path))

    # 삭제된 노드
    for name in (before_names - after_names):
        full_path = f"{path}/{name}" if path else name
        child = before.children[name]
        if child.is_file:
            result["deleted"].append(full_path)
        else:
            result["deleted"].extend(collect_all_files(child, full_path))

    # 양쪽에 존재하는 노드
    for name in (before_names & after_names):
        full_path = f"{path}/{name}" if path else name
        before_child = before.children[name]
        after_child = after.children[name]

        # 해시가 같으면 건너뜀 (핵심 최적화)
        if before_child.hash == after_child.hash:
            continue

        if before_child.is_file and after_child.is_file:
            result["modified"].append(full_path)
        elif not before_child.is_file and not after_child.is_file:
            # 디렉터리 → 재귀 탐색
            sub_result = diff_trees(before_child, after_child, full_path)
            result["created"].extend(sub_result["created"])
            result["modified"].extend(sub_result["modified"])
            result["deleted"].extend(sub_result["deleted"])
        else:
            # 파일↔디렉터리 전환 (드문 경우)
            result["deleted"].append(full_path)
            result["created"].append(full_path)

    return result
```

### 성능 비교

| 지표 | 해시 비교 (최소) | Merkle Tree (확장) |
|------|-----------------|-------------------|
| 변경 감지 복잡도 | O(n) | O(log n) |
| 스냅샷 생성 | O(n) — 모든 파일 해시 | O(n) — 최초 1회, 이후 O(k log n) |
| 메모리 사용 | O(n) | O(n) + 트리 오버헤드 |
| 구현 복잡도 | 낮음 | 중간 |
| 권장 파일 수 | ~1,000 이하 | 1,000+ |

---

## 델타 로그 연동

변경 감지 결과는 자동으로 델타 엔트리의 `files_changed` 필드를 생성한다.

### 파이프라인

```
[마일스톤 시작]
    │
    ▼
create_snapshot(project_root, "M{N}")  ─→ 시작 스냅샷 저장
    │
    ▼
[... 작업 수행 ...]
    │
    ▼
create_snapshot(project_root, "M{N}-end")  ─→ 완료 스냅샷 저장
    │
    ▼
compare_snapshots(start, end)  ─→ 변경 목록 생성
    │
    ▼
generate_files_changed(diff_result)  ─→ delta entry의 files_changed 필드
    │
    ▼
[에이전트가 summary 필드를 채움]  ─→ 각 파일 변경의 요약 생성
    │
    ▼
[델타 엔트리 완성]  ─→ delta-schema.json에 맞게 검증
```

### 변경 목록에서 델타 엔트리 생성

```python
def generate_files_changed(diff_result: dict) -> list[dict]:
    """비교 결과를 delta entry의 files_changed 형식으로 변환한다.
    summary 필드는 빈 문자열로 남겨두고, 에이전트가 채운다.

    Args:
        diff_result: compare_snapshots의 반환값

    Returns:
        files_changed 배열 (summary는 빈 문자열)
    """
    files_changed = []

    for item in diff_result["created"]:
        files_changed.append({
            "path": item["path"] if isinstance(item, dict) else item,
            "action": "created",
            "summary": ""  # 에이전트가 채움
        })

    for item in diff_result["modified"]:
        files_changed.append({
            "path": item["path"] if isinstance(item, dict) else item,
            "action": "modified",
            "summary": ""
        })

    for item in diff_result["deleted"]:
        files_changed.append({
            "path": item["path"] if isinstance(item, dict) else item,
            "action": "deleted",
            "summary": ""
        })

    return files_changed
```

---

## 캐싱 전략

### 콘텐츠 해시 → 요약 매핑

파일 내용이 변경되지 않았으면 이전에 생성한 요약을 재사용할 수 있다. 해시를 키로 요약을 캐시한다.

```json
{
  "cache_version": 1,
  "entries": {
    "a1b2c3d4e5f6...": {
      "path": "src/auth/jwt.py",
      "summary": "JWT 토큰 발급/검증 모듈. RS256, 만료 1시간",
      "created_at": "2026-03-10T15:30:00Z",
      "milestone": "M3"
    },
    "f6e5d4c3b2a1...": {
      "path": "src/models/user.py",
      "summary": "User 모델, role 필드 (admin/user/viewer)",
      "created_at": "2026-03-08T10:00:00Z",
      "milestone": "M2"
    }
  }
}
```

### 캐시 조회 흐름

```
파일 변경 감지
    │
    ▼
hash = SHA256(file_content)
    │
    ▼
cache에 hash 존재?
    │
    ├─ YES → 캐시된 summary 재사용 (LLM 호출 절약)
    │
    └─ NO → 에이전트가 summary 생성 → 캐시에 저장
```

### 캐시 관리

- **저장 위치**: `.agent-forge/cache/summaries.json`
- **최대 크기**: 500 엔트리
- **퇴거 정책**: LRU (Least Recently Used)
- **무효화**: 캐시 버전 변경 시 전체 무효화 (요약 형식 변경 등)

### 캐시 적중률 예상

| 프로젝트 유형 | 예상 적중률 | 근거 |
|-------------|-----------|------|
| 점진적 개발 (매 마일스톤 5-10 파일 변경) | 80-90% | 대부분의 파일이 변경되지 않음 |
| 대규모 리팩터링 | 20-40% | 많은 파일이 한꺼번에 변경됨 |
| 설정/문서 위주 변경 | 90-95% | 소스 코드 변경 거의 없음 |
