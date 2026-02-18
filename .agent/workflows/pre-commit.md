---
description: Quality gate to run before committing code changes
---

# Pre-Commit Quality Gate

Run these checks BEFORE every `git commit` to catch CI failures locally.

// turbo-all

## 1. Format Check (Black)

```bash
.venv\Scripts\python.exe -m black core/ tests/ tools/ backend/ --exclude="frontend|node_modules|.venv|venv"
```

Then verify formatting:
```bash
.venv\Scripts\python.exe -m black --check core/ tests/ tools/ backend/ --exclude="frontend|node_modules|.venv|venv"
```

Note: Black is configured via `pyproject.toml` (>=24.0.0) and uses 2024+ style.

## 2. Lint Check (Ruff)

```bash
.venv\Scripts\python.exe -m ruff check core/ tests/ backend/ --fix
```

## 3. Import Sort (isort)

```bash
.venv\Scripts\python.exe -m isort core/ tests/ backend/ --check-only
```

If this fails, run without `--check-only` to auto-fix.

## 4. Fast Test Gate

```bash
.venv\Scripts\python.exe -m pytest tests/ -m "not slow and not integration" -q
```

## 5. Commit

Only after all checks pass:
```bash
git add -A
git commit -m "your message"
```

Use `--no-verify` only if pre-commit hooks fail on unrelated pre-existing issues (e.g., pycache artifacts).
