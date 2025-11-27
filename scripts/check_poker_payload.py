import sys
import os

# Ensure project root is on sys.path when running as a script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.simulation_runner import SimulationRunner

runner = SimulationRunner()
state = runner.get_state(force_full=True)

# Print any poker events in the state
poker_events = state.to_dict().get('poker_events', [])
print('Poker events in state:', len(poker_events))
for ev in poker_events:
    print(ev)

# Now inject a synthetic plant event into the engine's event queue and rebuild state
engine = runner.world.engine
engine.poker_events.appendleft({
    'frame': engine.frame_count,
    'winner_id': -3,
    'loser_id': 1,
    'winner_hand': 'Triple',
    'loser_hand': 'Pair',
    'energy_transferred': 12.5,
    'message': 'Plant #2 beats Fish #1 with Triple! (+12.5⚡)',
    'is_plant': True,
    'plant_id': 2,
})

state2 = runner.get_state(force_full=True)
pe2 = state2.to_dict().get('poker_events', [])
print('\nAfter injecting synthetic event:')
for ev in pe2:
    print(ev)

# Directly call the internal collector to debug
collected = runner._collect_poker_events()
print('\nCollected via _collect_poker_events():', len(collected))
for ev in collected:
    print(ev.to_dict())
