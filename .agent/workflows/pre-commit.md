---
description: Quality gate to run before committing code changes
---

# Pre-Commit Quality Gate

Run these checks BEFORE every `git commit` to catch CI failures locally.

// turbo-all

## 1. Format Check (Black)

```bash
.venv\Scripts\python.exe -m black --check core/ tests/ backend/ --exclude="frontend|node_modules|.venv|venv"
```

If this fails, run without `--check` to auto-fix:
```bash
.venv\Scripts\python.exe -m black core/ tests/ backend/ --exclude="frontend|node_modules|.venv|venv"
```

## 2. Lint Check (Ruff)

```bash
.venv\Scripts\python.exe -m ruff check core/ tests/ backend/ --fix
```

## 3. Import Sort (isort)

```bash
.venv\Scripts\python.exe -m isort core/ tests/ backend/ --check-only
```

If this fails, run without `--check-only` to auto-fix.

## 4. Python 3.9 Compatibility

Avoid these patterns that require Python 3.10+:
- `int | None` → use `Optional[int]` from `typing`
- `list[str]` → use `List[str]` from `typing`
- `dict[str, Any]` → use `Dict[str, Any]` from `typing`
- `match` statements → use if/elif chains

## 5. Fast Test Gate

```bash
.venv\Scripts\python.exe -m pytest tests/ -m "not slow and not integration" -q
```

## 6. Commit

Only after all checks pass:
```bash
git add -A
git commit -m "your message"
```

Use `--no-verify` only if pre-commit hooks fail on unrelated pre-existing issues (e.g., pycache artifacts).
