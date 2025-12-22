# Tests Directory Structure

This directory contains all tests for the Tank simulation, organized by type.

## Test Categories

### Unit Tests (`tests/`)
Fast, isolated tests for individual components. These should:
- Run quickly (< 1 second each)
- Not require external resources (servers, databases)
- Test one thing at a time

### Integration Tests (`tests/integration/`)
Tests that verify multiple components work together. These may:
- Require a running server
- Test end-to-end workflows
- Take longer to run

### API Tests (`tests/api/`)
Tests for REST and WebSocket endpoints. These:
- Verify API contracts
- Test request/response formats
- May require a running backend

### Smoke Tests (`tests/smoke/`)
Quick sanity checks to verify basic functionality:
- Run after major changes
- Verify core imports work
- Test basic simulation startup

## Running Tests

```bash
# Run all unit tests
pytest tests/ -v

# Run only fast tests (skip integration)
pytest tests/ -v -m "not integration"

# Run integration tests
pytest tests/integration/ -v

# Run smoke tests (quick sanity check)
pytest tests/smoke/ -v

# Run with coverage
pytest tests/ --cov=core --cov-report=html
```

## Test Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test functions: `test_<behavior_being_tested>`
