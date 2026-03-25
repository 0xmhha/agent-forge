#!/bin/bash
# agent-forge installer — applies methodology to a target project
#
# Usage:
#   ./install.sh /path/to/target-project
#   ./install.sh /path/to/target-project --global   (install skills globally)
#   ./install.sh /path/to/target-project --full      (include review skills)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-.}"
MODE="${2:-}"

if [ ! -d "$TARGET" ]; then
  echo "Error: Target directory '$TARGET' does not exist."
  exit 1
fi

TARGET="$(cd "$TARGET" && pwd)"
echo "========================================"
echo " agent-forge installer"
echo "========================================"
echo ""
echo "Target: $TARGET"
echo "Mode:   ${MODE:-local}"
echo ""

# --- Determine skill set ---
CORE_SKILLS="complexity qr-gate delta-log milestone"
REVIEW_SKILLS="check-reviews do-review"

if [ "$MODE" = "--full" ]; then
  ALL_SKILLS="$CORE_SKILLS $REVIEW_SKILLS"
  SKILLS_DIR="$TARGET/.claude/skills"
  echo "[1/5] Installing all skills (core + review) to project"
elif [ "$MODE" = "--global" ]; then
  ALL_SKILLS="$CORE_SKILLS"
  SKILLS_DIR="$HOME/.claude/skills"
  echo "[1/5] Installing core skills globally to $SKILLS_DIR"
else
  ALL_SKILLS="$CORE_SKILLS"
  SKILLS_DIR="$TARGET/.claude/skills"
  echo "[1/5] Installing core skills to project"
fi

# --- Skills ---
mkdir -p "$SKILLS_DIR"
for skill in $ALL_SKILLS; do
  if [ -d "$SCRIPT_DIR/skills/$skill" ]; then
    mkdir -p "$SKILLS_DIR/$skill"
    cp "$SCRIPT_DIR/skills/$skill/SKILL.md" "$SKILLS_DIR/$skill/SKILL.md"
    echo "  + /$skill"
  else
    echo "  ! /$skill (not found, skipping)"
  fi
done

# --- Hooks ---
echo ""
echo "[2/5] Installing hooks"
HOOKS_TARGET="$TARGET/.claude/settings.json"
if [ -f "$HOOKS_TARGET" ]; then
  echo "  ! settings.json already exists. Skipping hooks."
  echo "    Merge manually from: $SCRIPT_DIR/hooks/settings.json"
else
  mkdir -p "$TARGET/.claude"
  cp "$SCRIPT_DIR/hooks/settings.json" "$HOOKS_TARGET"
  echo "  + pre-commit QR check"
  echo "  + session-end checklist"
fi

# --- delta-logs directory ---
echo ""
echo "[3/5] Creating delta-logs directory"
mkdir -p "$TARGET/delta-logs"
echo "  + delta-logs/"

# --- CLAUDE.md ---
echo ""
echo "[4/5] Installing CLAUDE.md template"
if [ -f "$TARGET/CLAUDE.md" ]; then
  echo "  ! CLAUDE.md already exists. Skipping."
  echo "    Template: $SCRIPT_DIR/templates/CLAUDE.md.template"
else
  cp "$SCRIPT_DIR/templates/CLAUDE.md.template" "$TARGET/CLAUDE.md"
  echo "  + CLAUDE.md (edit placeholders)"
fi

# --- Completion & Onboarding Guide ---
echo ""
echo "[5/5] Installation complete"
echo ""
echo "========================================"
echo " Onboarding Guide"
echo "========================================"
echo ""
echo "도입 우선순위 (순서대로 진행하세요):"
echo ""
echo "  Step 1: CLAUDE.md 편집"
echo "    - 프로젝트 설명, 아키텍처, 개발 명령어 작성"
echo "    - 커밋 규칙, 코드 표준 확인"
echo ""
echo "  Step 2: (선택) domain-profile.yaml 생성"
echo "    - 도메인별 QR 규칙 커스터마이징"
echo "    - 예시: phases/phase-2-domain-profiles/profiles/"
echo ""
echo "  Step 3: Claude Code 시작 → /complexity로 작업 시작"
echo "    - 작업 복잡도 평가 → Tier 자동 설정"
echo "    - 코딩 완료 후 → /milestone로 일괄 처리"
echo ""
echo "----------------------------------------"
echo " 30/60/90 Day Roadmap"
echo "----------------------------------------"
echo ""
echo "  Day 1-30:  기본 워크플로우 정착"
echo "    /complexity → 코딩 → /milestone"
echo "    delta-log 누적으로 프로젝트 이력 구축"
echo ""
echo "  Day 31-60: 도메인 커스터마이징"
echo "    domain-profile.yaml로 QR 규칙 조정"
echo "    rolling-summary 활용한 세션 간 컨텍스트 유지"
echo ""
echo "  Day 61-90: 측정 및 최적화"
echo "    token-monitor로 토큰 소비 추적"
echo "    워크플로우별 비용-품질 분석"
echo ""
echo "----------------------------------------"
echo " Available Commands"
echo "----------------------------------------"
echo ""
echo "  Core:"
echo "    /complexity  — 작업 복잡도 평가, Tier 설정"
echo "    /qr-gate     — 커밋 전 품질 검증"
echo "    /delta-log   — 마일스톤 기록 + rolling-summary 갱신"
echo "    /milestone   — 전체 완료 워크플로우 일괄 실행"
echo ""
if [ "$MODE" = "--full" ]; then
echo "  Review (--full mode):"
echo "    /check-reviews — 신규 코드 리뷰 요청 확인"
echo "    /do-review     — 코드 리뷰 sub-agent 실행"
echo ""
fi
echo "  Workflow: /complexity → coding → /milestone"
echo ""
