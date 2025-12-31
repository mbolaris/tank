# Python Code Pool

## Overview

The Python code pool is a small, deterministic subsystem for storing and compiling
user-provided Python snippets into callable policies. It is intentionally narrow:
code is parsed, validated against a strict AST sandbox, and executed with a reduced
set of globals. The result is cached by component ID + version for stable reuse.

## Threat Model (Basic)

The sandbox is designed to prevent obvious escapes and risky behavior:

- No imports (prevents access to os, sys, network, file system, etc.).
- No exec/eval/compile/open/globals/locals or dunder attribute access.
- No loops or comprehensions (avoids unbounded runtime without a step budget).

This is not a full security sandbox. It is a deterministic, low-risk execution
environment for small policy functions.

## Allowed Syntax and Globals

Allowed syntax is intentionally minimal:

- Literals, arithmetic, comparisons, boolean logic.
- If statements and simple function definitions.
- Return statements and simple assignments.

Explicitly disallowed:

- Imports, classes, decorators, loops, comprehensions, lambdas, try/except.
- Dunder names or dunder attribute access.
- Builtins that can escape or inspect the environment.

Allowed globals are restricted to a safe, deterministic set of builtins plus
explicitly injected modules (currently `math`). If randomness is needed, policies
must use the provided `rng` parameter and must not import or create random sources.

## Determinism

Determinism is enforced by:

- No implicit randomness (imports are blocked; no global random access).
- All stochastic behavior must come from an injected `rng` argument.
- Stable compilation cache keyed by component ID and version.

## Future Integration

The code pool is a substrate for evolved components. Future work will:

- Store component IDs in genomes to point at pool-managed policies.
- Track provenance and evaluation metadata alongside components.
- Introduce a step budget or gas meter to safely allow loops.
