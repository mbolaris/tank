# 🐠 Artificial Life Fish Tank Simulation

An advanced artificial life ecosystem simulation featuring genetics, evolution, energy systems, and emergent population dynamics.

## 🎯 Overview

This is a **comprehensive ALife simulation** built with Pygame that demonstrates complex ecosystem behaviors through simple rules. Fish have genetics, require food to survive, reproduce with genetic mixing, and evolve over generations. The simulation features day/night cycles, living plants that produce food, and rich population dynamics.

## ✨ Features

### 🧬 Genetics & Evolution
- **Heritable Traits**: Fish inherit genetic traits from both parents
  - Speed modifier (affects swimming speed)
  - Size modifier (visual size variation)
  - Vision range (detection radius)
  - Metabolism rate (energy consumption)
  - Max energy (stamina and lifespan)
  - Fertility (reproduction rate)
  - Aggression (territorial behavior)
  - Social tendency (schooling preference)
  - Color hue (visual diversity)

- **Mutation**: Small random variations occur during reproduction
- **Natural Selection**: Fish with better-adapted genetics survive longer and reproduce more
- **Visual Diversity**: Each fish has a unique color tint based on genetics

### 🔋 Energy & Metabolism
- **Energy System**: Fish start with full energy that depletes over time
- **Metabolism**: Energy consumption based on:
  - Base metabolic rate (influenced by genetics)
  - Movement speed (faster movement = more energy)
  - Life stage (babies need less, elders need more)
  - Time of day (reduced metabolism at night)

- **Food Consumption**: Fish must eat to survive
  - Gain 40 energy per food item
  - Plants produce food automatically
  - Food sinks to the bottom

- **Death by Starvation**: Fish die when energy reaches 0

### 🌱 Life Cycles
- **Age Progression**: Fish age in real-time (frames)
- **Life Stages**:
  - **Baby** (0-10 sec): Small size, grows, reduced metabolism
  - **Juvenile** (10-30 sec): Full size, actively exploring
  - **Adult** (30 sec - 2 min): Can reproduce, peak performance
  - **Elder** (2+ min): Increased metabolism, nearing natural death

- **Natural Death**: Fish die from old age after ~3 minutes (genetically variable)

### 👶 Reproduction
- **Requirements**:
  - Adult life stage
  - Energy above 60% (60/100)
  - Nearby mate of same species
  - Cooldown period expired (20 seconds between attempts)

- **Pregnancy System**:
  - 10-second gestation period
  - Energy cost for reproduction (-20 energy)
  - Offspring spawns near parent

- **Genetic Mixing**: Offspring genome created from both parents with mutations
- **Population Control**: Carrying capacity of 50 fish prevents overpopulation

### 🌍 Living Ecosystem
- **Day/Night Cycles**:
  - Full cycle every ~1 minute (1800 frames at 30fps)
  - Visual effects (screen tinting, brightness changes)
  - Reduced fish activity at night
  - Lower metabolism during nighttime

- **Food Production**:
  - 3 plants produce food automatically
  - Production every 5 seconds per plant
  - Max 8 food items per plant
  - Faster production during daytime

- **Ecosystem Balance**:
  - Sustainable population with proper food supply
  - Birth/death tracking
  - Generation counter
  - Death cause analysis (starvation, old age, predation)

### 📊 Statistics & Visualization
- **Real-time Stats Panel**:
  - Current time of day (Dawn/Day/Dusk/Night)
  - Population count / carrying capacity
  - Current generation number
  - Total births and deaths
  - Capacity usage percentage
  - Death causes breakdown

- **Health Bars**: Color-coded energy bars above each fish
  - Green: Healthy (>60% energy)
  - Yellow: Medium (30-60% energy)
  - Red: Starving (<30% energy)

- **Visual Effects**:
  - Day/night screen tinting
  - Genetic color variations
  - Size scaling based on life stage and genetics
  - Smooth animations

## 🎮 Controls

| Key | Action |
|-----|--------|
| **SPACE** | Drop food manually |
| **P** | Pause/Resume simulation |
| **ESC** | Quit simulation |

## 🚀 Running the Simulation

### Requirements
```bash
pip install pygame
```

### Start the Simulation
```bash
python fishtank.py
```

### Run Tests
```bash
# Quick test (100 frames)
python test_simulation.py

# Run existing test suite
pytest tests/
```

## 📁 Project Structure

```
tank/
├── fishtank.py              # Main simulation loop & game logic
├── agents.py                # Fish, Plant, Food, Crab, Castle classes
├── genetics.py              # Genome system & inheritance
├── ecosystem.py             # Population tracking & statistics
├── time_system.py           # Day/night cycle management
├── environment.py           # Agent query methods
├── movement_strategy.py     # Fish movement behaviors
├── constants.py             # Configuration parameters
├── image_loader.py          # Asset loading
├── test_simulation.py       # Integration test
├── tests/                   # Unit test suite
│   ├── test_agents.py
│   ├── test_movement_strategy.py
│   ├── test_collision.py
│   ├── test_integration.py
│   └── conftest.py
└── images/                  # Sprite assets
```

## 🔧 Configuration

Key parameters in `constants.py`:

```python
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FRAME_RATE = 30
NUM_SCHOOLING_FISH = 6
```

Key parameters in `agents.py`:

```python
# Fish
BASE_MAX_ENERGY = 100.0
ENERGY_FROM_FOOD = 40.0
BASE_METABOLISM = 0.015
BABY_AGE = 300  # 10 seconds
ADULT_AGE = 1800  # 1 minute
BASE_MAX_AGE = 5400  # 3 minutes

# Plants
BASE_FOOD_PRODUCTION_RATE = 150  # 5 seconds
MAX_FOOD_CAPACITY = 8  # per plant
```

Key parameters in `time_system.py`:

```python
cycle_length = 1800  # Full day/night cycle (60 seconds at 30fps)
```

## 🧪 Ecosystem Dynamics Observed

### Sustainable Population
- With 3 plants and balanced metabolism, population grows steadily
- Initial 7 fish → 15+ fish over 90 seconds
- First births occur around 40 seconds (frame 1200)
- Generation 0 → Generation 1 transition observed

### Natural Selection (Long-term)
- Fish with better metabolism survive longer
- High-fertility genetics spread through population
- Efficient foragers pass on vision/speed traits

### Population Crashes (if unbalanced)
- Too many fish → food scarcity → starvation
- Predators (crab) can decimate population
- Ecosystem can recover if survivors reproduce

## 🐛 Known Limitations

1. **Crab Predator**: Currently disabled as it's too effective at hunting
2. **No Genetic Drift Visualization**: Can't see trait evolution graphs in real-time
3. **Fixed Plant Positions**: Plants don't grow or spread
4. **Simple AI**: Movement strategies are rule-based, not learned

## 🎓 Educational Value

This simulation demonstrates:
- **Genetics & Heredity**: Mendelian inheritance with mutations
- **Natural Selection**: Survival of the fittest in action
- **Population Dynamics**: Carrying capacity, birth/death rates
- **Energy Flow**: Producers (plants) → Consumers (fish)
- **Emergent Behavior**: Complex ecosystem from simple rules
- **Life Cycles**: Birth, growth, reproduction, death

## 🔬 Future Enhancements

Potential additions:
- [ ] Neural network fish brains (learning)
- [ ] Predator-prey balance improvements
- [ ] Genetic trait evolution graphs
- [ ] Save/load ecosystem states
- [ ] Multiple species with different niches
- [ ] Seasonal variations
- [ ] Water quality parameters
- [ ] Disease/parasites system
- [ ] Territorial behavior implementation
- [ ] Sexual dimorphism (male/female)

## 📜 License

This project is open source. Feel free to modify and extend!

## 🙏 Credits

Built with:
- **Pygame**: Game engine and graphics
- **Python 3.11+**: Core language
- **Love for ALife**: Inspired by Conway's Life, Tierra, and evolutionary algorithms

---

**Enjoy watching life evolve! 🌊🐠✨**
