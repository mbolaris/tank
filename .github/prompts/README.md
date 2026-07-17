# GitHub Copilot prompt files

These are ports of the Claude Code commands in `.claude/commands/` for **GitHub Copilot**
(`*.prompt.md`). Unlike Codex, Copilot discovers these directly from the repo: with prompt
files enabled in VS Code, open Copilot Chat and run:

```
/deliberate
/build-elected
```

Notes:

- Copilot prompt files do not support Claude's `$ARGUMENTS` substitution. The server URL is
  documented as the default `http://127.0.0.1:8000`; replace the `<URL>` placeholder in the
  commands (or tell Copilot the server/proposal id in chat) when it differs.
- Requires the "prompt files" experience (VS Code setting `chat.promptFiles`). The Copilot
  coding agent and CLI also read repo `AGENTS.md`, which stays authoritative for
  contribution rules.
- Keep these in sync with `.claude/commands/` when the board protocol changes.
