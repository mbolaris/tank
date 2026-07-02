import unittest
from enum import Enum

from core.state_machine import StateMachine


class _TestState(Enum):
    A = "a"
    B = "b"


class TestStateMachineHistoryLimit(unittest.TestCase):
    def test_history_limit(self) -> None:
        """StateMachine history should be capped to max_history."""
        transitions = {_TestState.A: [_TestState.B], _TestState.B: [_TestState.A]}
        machine: StateMachine[_TestState] = StateMachine(
            _TestState.A,
            transitions,
            track_history=True,
            max_history=50,
        )

        for frame in range(200):
            target = _TestState.B if machine.state == _TestState.A else _TestState.A
            machine.transition(target, frame=frame)

        history = machine.history
        self.assertEqual(len(history), 50)
        self.assertEqual(history[0].frame, 150)
        self.assertEqual(history[-1].frame, 199)


if __name__ == "__main__":
    unittest.main()
