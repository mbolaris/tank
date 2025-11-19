# AI Code Evolution - Quick Start Guide

**Automatically improve fish behaviors using AI in 5 minutes!**

---

## Prerequisites

```bash
# Install AI dependencies (one-time setup)
pip install -e ".[ai]"

# Set up API key (choose one)
export ANTHROPIC_API_KEY="sk-ant-..."
# OR
export OPENAI_API_KEY="sk-..."
```

---

## The 5-Minute Workflow

### Step 1: Run Simulation (2 minutes)

```bash
python main.py --headless --max-frames 10000 --export-stats results.json
```

This runs a fast headless simulation and exports performance data.

### Step 2: Run AI Agent (2 minutes)

```bash
python scripts/ai_code_evolution_agent.py results.json --provider anthropic
```

The AI will:
- Identify the worst performing algorithm
- Analyze why it's failing
- Generate improved code
- Create a git branch with the fix

### Step 3: Review Changes (1 minute)

```bash
# See what changed
git diff HEAD~1

# Test it (optional)
python main.py --headless --max-frames 1000
```

### Step 4: Push (30 seconds)

```bash
git push -u origin <branch-name>

# Create PR
gh pr create --fill
```

That's it! You've just used AI to improve your simulation. 🎉

---

## What Just Happened?

The AI agent:

1. **Loaded** `results.json` with algorithm performance stats
2. **Found** the algorithm with lowest reproduction rate
3. **Read** its source code (using the algorithm registry)
4. **Called** Claude/GPT-4 to generate improvements
5. **Wrote** the improved code back to the file
6. **Created** a git branch with detailed commit message

---

## Example Results

**Before AI Improvement:**
```
Algorithm: freeze_response
Reproduction Rate: 0.0% 💀
Avg Lifespan: 492 frames
Death Cause: 100% starvation
```

**After AI Improvement:**
```
Algorithm: freeze_response
Reproduction Rate: 100.0% 🎉
Avg Lifespan: 15,000+ frames (still alive!)
Death Cause: 0% starvation
```

**Improvement: 0% → 100% reproduction rate!**

---

## Options

### Use Different LLM Provider

```bash
# Use Claude (default, recommended)
python scripts/ai_code_evolution_agent.py results.json --provider anthropic

# Use GPT-4
python scripts/ai_code_evolution_agent.py results.json --provider openai
```

### Dry Run (Test Without Committing)

```bash
python scripts/ai_code_evolution_agent.py results.json --dry-run
```

This shows what would change without actually modifying files or creating commits.

### Run Multiple Iterations

```bash
# Demo script: improve 3 algorithms in a row
bash scripts/demo_evolution_loop.sh 3
```

---

## Troubleshooting

### "No algorithm to improve found"

Not enough data. Run a longer simulation:

```bash
python main.py --headless --max-frames 50000 --export-stats results.json
```

### "ANTHROPIC_API_KEY not set"

Set your API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "Source file not found"

The algorithm isn't in the registry. Make sure it's listed in `core/algorithms/__init__.py`.

### AI Generated Broken Code

This happens sometimes. Just:

1. Review the diff
2. Reject the PR if broken
3. Run the agent again (it will try a different approach)

---

## Next Steps

- **Read the full guide**: `docs/AI_CODE_EVOLUTION_WORKFLOW.md`
- **See the proof**: `docs/PROOF_OF_AI_IMPROVEMENT.md`
- **Customize the prompt**: Edit `scripts/ai_code_evolution_agent.py`
- **Set up CI/CD**: Run this workflow automatically on every simulation

---

## The Big Picture

```
┌─────────────────┐
│ Run Simulation  │──> results.json
└────────┬────────┘
         │
         v
┌─────────────────┐
│   AI Agent      │──> Find worst algorithm
│  (Claude/GPT)   │──> Generate fix
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Git Branch     │──> ai-improve-<algo>-<date>
│  + Commit       │
└────────┬────────┘
         │
         v
┌─────────────────┐
│   Pull Request  │──> You review and merge
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Repeat! 🔄     │──> Continuous evolution
└─────────────────┘
```

**This is your AI Junior Developer working 24/7 to improve the codebase!** 🚀

---

## Safety Features

✅ **Human in the loop** - You review every change
✅ **Git history** - Full audit trail
✅ **No self-modification** - Simulation never edits itself
✅ **Rollback** - Easy to revert if needed
✅ **Test before merge** - Run validation before accepting changes

**Safe, debuggable, and effective!**
