from core.entities.base import Castle
from core.environment import Environment

env = Environment()
castle = Castle(env)
print("width:", castle.width)
print("height:", castle.height)
print("rect.width:", castle.rect.width)
print("rect.height:", castle.rect.height)
