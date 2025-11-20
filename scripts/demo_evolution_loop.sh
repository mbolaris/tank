#!/bin/bash
# Demo: AI Code Evolution Loop
#
# This script demonstrates the full continuous improvement workflow:
# 1. Run simulation
# 2. Analyze results with AI
# 3. Generate improvements
# 4. Review and test
# 5. Repeat

set -e

echo "=================================================="
echo "AI Code Evolution Demo"
echo "=================================================="
echo ""

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: Please set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable"
    echo ""
    echo "Example:"
    echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
    echo "  export OPENAI_API_KEY='sk-...'"
    exit 1
fi

# Determine provider
PROVIDER="anthropic"
if [ -n "$OPENAI_API_KEY" ]; then
    PROVIDER="openai"
fi

echo "Using LLM provider: $PROVIDER"
echo ""

# Number of iterations
ITERATIONS=${1:-3}
echo "Running $ITERATIONS improvement iterations"
echo ""

for i in $(seq 1 $ITERATIONS); do
    echo "=================================================="
    echo "Iteration $i/$ITERATIONS"
    echo "=================================================="
    echo ""

    # Step 1: Run simulation
    echo "Step 1: Running simulation (10,000 frames)..."
    python ../main.py --headless --max-frames 10000 --export-stats results.json
    echo ""

    # Step 2: Run AI agent
    echo "Step 2: Running AI Code Evolution Agent..."
    python ai_code_evolution_agent.py results.json --provider $PROVIDER
    echo ""

    # Step 3: Show the diff
    echo "Step 3: Showing what changed..."
    git diff HEAD~1 --stat
    echo ""

    # Step 4: Quick test
    echo "Step 4: Quick validation test (1,000 frames)..."
    python ../main.py --headless --max-frames 1000
    echo ""

    # Step 5: Ask user to continue
    if [ $i -lt $ITERATIONS ]; then
        echo "Iteration $i complete!"
        echo ""
        read -p "Continue to iteration $((i+1))? [Y/n] " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo "Stopping at user request"
            break
        fi
        echo ""
    fi
done

echo "=================================================="
echo "Evolution Loop Complete!"
echo "=================================================="
echo ""
echo "Review all branches created:"
git branch | grep "ai-improve"
echo ""
echo "To push all branches:"
echo "  git push --all origin"
echo ""
echo "To create pull requests:"
echo "  gh pr create --fill"
