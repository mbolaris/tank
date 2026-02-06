#!/bin/bash
set -euo pipefail

# Only run in remote (Claude Code on the web) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Install Python dependencies (core + dev tools: pytest, black, ruff, mypy)
pip install -e ".[dev]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Install frontend dependencies
cd "$CLAUDE_PROJECT_DIR/frontend"
npm install
cd "$CLAUDE_PROJECT_DIR"

# Set PYTHONPATH for scripts that need it
echo 'export PYTHONPATH="."' >> "$CLAUDE_ENV_FILE"
