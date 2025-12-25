#!/usr/bin/env python
import subprocess
import os
from pathlib import Path

os.chdir(str(Path(__file__).parent.parent))

# Stage all changes
print('Staging changes...')
subprocess.run(['git', 'add', '-A'], check=True)

# Commit with message
message = """Fixes: genome serialization compatibility, trait clamping, remove legacy screen args, fix spawn_auto_food syntax

- Accept legacy genome kwargs (behavior_algorithm, poker_algorithm) in codec
- Clamp trait values during deserialization to TraitSpec bounds
- Add defensive checks in Genome computed properties
- Remove legacy screen_width/screen_height kwargs from spawn/add-food call sites and tests
- Fix unmatched parenthesis in spawn_auto_food method"""

print('Committing...')
result = subprocess.run(['git', 'commit', '-m', message], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr)
print('Return code:', result.returncode)

# Show the commit
print('\nCommit created:')
subprocess.run(['git', 'log', '--oneline', '-1'], check=True)
