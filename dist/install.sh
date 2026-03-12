#!/bin/bash
# agent-forge installer — applies methodology to a target project
#
# Usage:
#   ./install.sh /path/to/target-project
#   ./install.sh /path/to/target-project --global   (install skills globally)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-.}"
GLOBAL_MODE="${2:-}"

if [ ! -d "$TARGET" ]; then
  echo "Error: Target directory '$TARGET' does not exist."
  exit 1
fi

TARGET="$(cd "$TARGET" && pwd)"
echo "[agent-forge] Installing to: $TARGET"

# --- Skills ---
if [ "$GLOBAL_MODE" = "--global" ]; then
  SKILLS_DIR="$HOME/.claude/skills"
  echo "[agent-forge] Installing skills globally to $SKILLS_DIR"
else
  SKILLS_DIR="$TARGET/.claude/skills"
  echo "[agent-forge] Installing skills to project: $SKILLS_DIR"
fi

mkdir -p "$SKILLS_DIR"
for skill in complexity qr-gate delta-log milestone; do
  mkdir -p "$SKILLS_DIR/$skill"
  cp "$SCRIPT_DIR/skills/$skill/SKILL.md" "$SKILLS_DIR/$skill/SKILL.md"
  echo "  Installed: /$skill"
done

# --- Hooks ---
HOOKS_TARGET="$TARGET/.claude/settings.json"
if [ -f "$HOOKS_TARGET" ]; then
  echo "[agent-forge] Warning: $HOOKS_TARGET already exists. Skipping hooks."
  echo "  Merge manually from: $SCRIPT_DIR/hooks/settings.json"
else
  mkdir -p "$TARGET/.claude"
  cp "$SCRIPT_DIR/hooks/settings.json" "$HOOKS_TARGET"
  echo "  Installed: hooks (pre-commit QR check, session-end checklist)"
fi

# --- delta-logs directory ---
mkdir -p "$TARGET/delta-logs"
echo "  Created: delta-logs/"

# --- CLAUDE.md ---
if [ -f "$TARGET/CLAUDE.md" ]; then
  echo "[agent-forge] Warning: CLAUDE.md already exists. Skipping."
  echo "  Template available at: $SCRIPT_DIR/templates/CLAUDE.md.template"
else
  cp "$SCRIPT_DIR/templates/CLAUDE.md.template" "$TARGET/CLAUDE.md"
  echo "  Created: CLAUDE.md (edit placeholders)"
fi

echo ""
echo "[agent-forge] Installation complete."
echo ""
echo "Next steps:"
echo "  1. Edit CLAUDE.md — fill in project-specific sections"
echo "  2. (Optional) Create domain-profile.yaml for domain-specific QR rules"
echo "  3. Start Claude Code in your project and use /complexity to begin"
echo ""
echo "Available commands:"
echo "  /complexity  — Assess task complexity and set workflow tier"
echo "  /qr-gate     — Run quality review before commit"
echo "  /delta-log   — Record milestone delta and rolling summary"
echo "  /milestone   — Run full completion workflow"
