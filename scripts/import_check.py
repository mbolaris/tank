import importlib
import sys

modules = [
    'core.poker.betting.decision',
    'core.poker.core.game_state',
    'core.poker.simulation.engine',
]

ok = True
for m in modules:
    try:
        importlib.import_module(m)
        print(f'OK: {m}')
    except Exception as e:
        print(f'ERR: {m} -> {e}')
        ok = False

if not ok:
    sys.exit(2)
else:
    sys.exit(0)
