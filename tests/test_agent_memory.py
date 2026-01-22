from core.agent_memory import AgentMemorySystem as FishMemorySystem
from core.agent_memory import MemoryType
from core.math_utils import Vector2


def test_memories_expire_based_on_frames():
    system = FishMemorySystem()
    system.current_frame = 100

    system.add_memory(MemoryType.FOOD_LOCATION, Vector2(10, 10))
    assert system.get_memory_count(MemoryType.FOOD_LOCATION) == 1

    # Advance fewer frames than the max_age window to ensure memory persists
    system.update(current_frame=150)
    assert system.get_memory_count(MemoryType.FOOD_LOCATION) == 1

    # Move well past the max_age window; memory should expire
    system.update(current_frame=2000)
    assert system.get_memory_count(MemoryType.FOOD_LOCATION) == 0
