import sys
import os
import unittest
from unittest.mock import MagicMock

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.auto_eval_service import AutoEvalService

class TestAutoEvalServiceLeak(unittest.TestCase):
    def test_history_limit(self):
        # Mock dependencies
        world = MagicMock()
        service = AutoEvalService(world)
        
        # Manually inject history items
        service.history = [{"hand": i} for i in range(200)]
        
        # Trigger update_stats with a dummy final_stats object
        # We need a dummy object that has the attributes accessed in _update_stats
        class DummyStats:
            hands_played = 100
            hands_remaining = 0
            game_over = True
            winner = "Test"
            reason = "Test"
            players = []
            performance_history = [{"hand": 100}] # New item to append

        final_stats = DummyStats()
        
        # Call the method that updates stats and trims history
        # Note: _update_stats is intended to be called internally, so we simulate the call
        service._update_stats(final_stats)
        
        print(f"History length after update: {len(service.history)}")
        
        # Expected limit is 50
        self.assertLessEqual(len(service.history), 50)
        
        # Ensure we kept the LATEST items (plus the one we just added)
        # The logic appends then slices. 
        # We started with 0..199. Appended one item. Then sliced to last 50.
        # So last item should be the new one.
        # Check defaults from code:
        # starting_hand logic uses service.history[-1] if exists
        
        # Let's verify via the actual logic
        # logic:
        # starting_hand = self.history[-1]["hand"] if self.history else 0
        # ... append adjusted snapshot ...
        # self.stats = ...
        # if len(self.history) > MAX_HISTORY_ITEMS: self.history = self.history[-MAX_HISTORY_ITEMS:]
        
        # We manually set history to 200 items. 
        # _update_stats runs.
        # It appends one more item from performance_history.
        # Then it slices to 50.
        
        self.assertEqual(len(service.history), 50)

if __name__ == "__main__":
    unittest.main()
