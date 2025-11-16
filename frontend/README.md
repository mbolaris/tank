# Fish Tank Simulation - React Frontend

Modern React + TypeScript + Vite frontend for the fish tank simulation with real-time Canvas rendering.

## Features

- Real-time WebSocket connection to simulation backend
- Canvas-based rendering (60 FPS capable)
- Interactive controls (Add Food, Pause/Resume, Reset)
- Live statistics panel
- Responsive design
- Species color-coding
- Energy bars on fish
- Beautiful dark theme

## Installation

```bash
cd frontend
npm install
```

## Running the Frontend

Make sure the backend is running first (see `backend/README.md`), then:

```bash
npm run dev
```

The frontend will start on `http://localhost:5173`

## Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Canvas.tsx           # Canvas rendering component
│   │   ├── ControlPanel.tsx     # Control buttons
│   │   └── StatsPanel.tsx       # Statistics display
│   ├── hooks/
│   │   └── useWebSocket.ts      # WebSocket connection hook
│   ├── types/
│   │   └── simulation.ts        # TypeScript type definitions
│   ├── utils/
│   │   └── renderer.ts          # Canvas rendering logic
│   ├── App.tsx                  # Main app component
│   ├── App.css                  # App styles
│   ├── index.css                # Global styles
│   └── main.tsx                 # Entry point
├── package.json
└── vite.config.ts
```

## Features Breakdown

### Canvas Rendering

The Canvas component renders all entities:
- **Fish**: Color-coded by species (Neural=cyan, Algorithmic=yellow, Schooling=blue, Solo=red)
- **Food**: Brown circles
- **Plants**: Green seaweed with wavy stems
- **Crab**: Orange with claws
- **Castle**: Gray structure with towers

Each fish displays an energy bar above it (green/yellow/red based on energy level).

### WebSocket Communication

The `useWebSocket` hook manages:
- Automatic connection to `ws://localhost:8000/ws`
- Real-time state updates at 30 FPS
- Command sending (add_food, pause, resume, reset)
- Auto-reconnection on disconnect

### Control Panel

Interactive controls:
- **Add Food**: Drop food into the tank
- **Pause/Resume**: Toggle simulation
- **Reset**: Restart with fresh population
- Connection status indicator

### Stats Panel

Real-time statistics:
- Current time of day
- Frame count
- Population counts (fish, food, plants)
- Generation number
- Birth/death totals
- Capacity usage
- Death causes breakdown
- Species legend

## Technology Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Canvas API** - High-performance rendering
- **WebSocket API** - Real-time communication

## Development Notes

### WebSocket Connection

The frontend expects the backend to be running on `http://localhost:8000`. To change this, edit `WS_URL` in `src/hooks/useWebSocket.ts`.

### Rendering Performance

The Canvas renderer is optimized for 30+ FPS updates with hundreds of entities. Each entity type has a custom rendering function in `utils/renderer.ts`.

### Type Safety

All simulation data structures are typed in `types/simulation.ts`, matching the backend Pydantic models.

## Responsive Design

The UI adapts to different screen sizes:
- **Desktop (>1200px)**: Sidebar on the right
- **Tablet (768-1200px)**: Sidebar below canvas
- **Mobile (<768px)**: Stacked layout

## Browser Compatibility

Requires a modern browser with:
- ES2020+ JavaScript support
- WebSocket support
- Canvas 2D API
- CSS Grid and Flexbox

## Future Enhancements

Potential additions:
- [ ] D3.js graphs for trait evolution over time
- [ ] Zoom/pan controls for canvas
- [ ] Click on fish to see detailed info
- [ ] Speed controls (faster/slower simulation)
- [ ] Save/load simulation state
- [ ] Replay mode to watch evolution history
- [ ] Dark/light theme toggle
- [ ] Export statistics to CSV
