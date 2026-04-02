#!/bin/bash
# Install deep-plan-enhanced skills into ~/.claude/skills/
# Run: bash install.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"
SETTINGS="$HOME/.claude/settings.json"

echo "Installing deep-plan-enhanced..."

# Copy skills
mkdir -p "$SKILLS_DIR"
cp -r "$SCRIPT_DIR/deep-plan" "$SKILLS_DIR/deep-plan"
cp -r "$SCRIPT_DIR/deep-implement" "$SKILLS_DIR/deep-implement"

# Install Python dependencies for deep-plan
if command -v uv &>/dev/null; then
    echo "Installing deep-plan dependencies with uv..."
    cd "$SKILLS_DIR/deep-plan" && uv sync --quiet
else
    echo "WARNING: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "Then run: cd $SKILLS_DIR/deep-plan && uv sync"
fi

echo ""
echo "Skills installed to:"
echo "  $SKILLS_DIR/deep-plan/"
echo "  $SKILLS_DIR/deep-implement/"
echo ""
echo "Next: Add hooks to $SETTINGS"
echo "See README.md for the hooks configuration to add."
echo ""
echo "Done."
