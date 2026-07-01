# Codex CLI custom prompts

These are ports of the Claude Code commands in `.claude/commands/` for the OpenAI
**Codex CLI**. Codex does **not** auto-discover prompts from the repo — it reads them
from `$CODEX_HOME/prompts/` (default `~/.codex/prompts/`). Install them once per machine:

```bash
mkdir -p ~/.codex/prompts
cp .codex/prompts/deliberate.md .codex/prompts/build-elected.md ~/.codex/prompts/
```

Then invoke inside a Codex session:

```
/deliberate                       # uses the default server http://127.0.0.1:8000
/deliberate http://host:8000      # $ARGUMENTS overrides the URL
/build-elected http://host:8000 14
```

`$ARGUMENTS` is substituted by Codex at invocation time (same role as in the Claude
version). Keep these in sync with `.claude/commands/` when the board protocol changes.
