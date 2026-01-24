# Tank World - React Frontend

Modern React + TypeScript + Vite frontend for Tank World with real-time Canvas rendering and Tank World Net support.

## Features

- Real-time WebSocket connection to simulation backend
- Canvas-based rendering (60 FPS capable)
- Interactive controls (Add Food, Pause/Resume, Reset)
- Live statistics panel
- Responsive design
- Species color-coding
- Energy bars on fish
- Beautiful dark theme
- **Tank World Net**: Multi-tank dashboard and management

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

## Routes

The application uses React Router for navigation:

| Route | Description |
|-------|-------------|
| `/` | Default tank view - connects to the server's default tank |
| `/tank/:tankId` | Specific tank view - connects to a tank by UUID |
| `/network` | Tank World Net dashboard - view and manage all tanks |

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Canvas.tsx           # Canvas rendering component
│   │   ├── ControlPanel.tsx     # Control buttons
│   │   ├── TankView.tsx         # Full tank view (canvas + controls + poker)
│   │   ├── StatsPanel.tsx       # Statistics display
│   │   ├── PhylogeneticTree.tsx # Evolution tree visualization
│   │   ├── PokerGame.tsx        # Poker game interface
│   │   ├── PokerDashboard.tsx   # Poker stats overview
│   │   ├── PokerLeaderboard.tsx # Poker rankings
│   │   ├── PokerEvents.tsx      # Real-time poker events
│   │   ├── AutoEvaluateDisplay.tsx # Auto-evaluation progress
│   │   ├── poker/               # Poker sub-components
│   │   └── ui/                  # Reusable UI components
│   ├── pages/
│   │   └── NetworkDashboard.tsx # Tank World Net management page
│   ├── hooks/
│   │   └── useWebSocket.ts      # WebSocket connection hook
│   ├── types/
│   │   └── simulation.ts        # TypeScript type definitions
│   ├── utils/
│   │   ├── renderer.ts          # Canvas rendering logic
│   │   ├── ImageLoader.ts       # Asset preloading
│   │   ├── fishTemplates.ts     # Fish visual templates
│   │   ├── fractalPlant.ts      # L-system plant rendering
│   │   └── lineageUtils.ts      # Phylogenetic tree data
│   ├── App.tsx                  # Main app with routing
│   ├── App.css                  # App styles
│   ├── config.ts                # Server configuration
│   ├── index.css                # Global styles
│   └── main.tsx                 # Entry point with BrowserRouter
├── package.json
└── vite.config.ts
```

## Tank World Net

Tank World Net enables running and viewing multiple independent tank simulations.

### Network Dashboard (`/network`)

The dashboard provides:
- **Tank List**: View all tanks with live status (running/paused/stopped)
- **Tank Stats**: Frame count, viewer count, owner
- **Create Tank**: Form to create new tank simulations
- **Delete Tank**: Remove tanks (with confirmation)
- **View Tank**: Navigate to any tank's live view

### Single Tank / Network View Toggle

- The top navigation includes a prominent view toggle for switching between the Single Tank view and the Network dashboard.
- When viewing a single tank there's a compact Tank Navigator next to the toggle (left/right arrows) that lets you quickly cycle between available tanks without opening the network dashboard.
- Keyboard shortcuts: use the left/right arrow keys (`←` / `→`) to switch tanks when viewing a single tank. A keyboard hint is shown in the navbar.
- The previous "View all tanks →" button has been removed — use the Network toggle to open the dashboard.

### Multi-Tank Support

- Each tank runs independently with its own simulation
- URL parameter `?tank={uuid}` connects to a specific tank
- WebSocket connections are per-tank
- Phylogenetic tree data is per-tank

### Connecting to Remote Servers

Use URL parameters to connect to remote Tank World Net servers:

```
http://localhost:5173?server=ws://192.168.1.100:8000
http://localhost:5173/network?server=ws://remote-server:8000
http://localhost:5173/tank/abc-123?server=ws://remote-server:8000
```

## Features Breakdown

### Canvas Rendering

The Canvas component renders all entities:
- **Fish**: Color-coded by species, with genetic variations
- **Food**: Brown circles
- **Plants**: L-system fractal plants with genetic evolution
- **Crab**: Orange with claws
- **Castle**: Gray structure with towers

Each fish displays an energy bar above it (green/yellow/red based on energy level).

### WebSocket Communication

The `useWebSocket(tankId?)` hook manages:
- Automatic connection to backend WebSocket
- Tank-specific connections when `tankId` is provided
- Real-time state updates at 30 FPS
- Delta compression for bandwidth efficiency
- Command sending (add_food, pause, resume, reset, poker actions)
- Auto-reconnection on disconnect

### Control Panel

Interactive controls:
- **Play Poker**: Start a poker game with fish
- **Add Food**: Drop food into the tank
- **Spawn Fish**: Add a new fish
- **Pause/Resume**: Toggle simulation
- **Fast Forward**: Run at 10x speed
- **Reset**: Restart with fresh population
- **Toggle Tree**: Show phylogenetic tree
- Connection status indicator

### Poker System

Fish can play Texas Hold'em poker:
- Interactive poker interface with betting
- AI autopilot option
- Leaderboard tracking wins/losses
- Real-time event feed
- Auto-evaluation benchmarks

### Stats Panel

Real-time statistics:
- Current time of day
- Frame count and FPS
- Population counts (fish, food, plants)
- Generation number
- Birth/death totals
- Capacity usage
- Death causes breakdown
- Energy distribution
- Poker statistics

## Technology Stack

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **Canvas API** - High-performance rendering
- **WebSocket API** - Real-time communication
- **react-d3-tree** - Phylogenetic tree visualization

## Configuration

The `config.ts` module handles server configuration:

```typescript
// Priority order:
// 1. URL query parameter (?server=ws://... and/or ?tank=uuid)
// 2. Environment variable (VITE_WS_URL, VITE_API_URL)
// 3. Default to same host as page

config.wsUrl           // WebSocket URL
config.apiBaseUrl      // HTTP API base URL
config.tankId          // Current tank ID from URL
config.serverDisplay   // Server display string
config.tanksApiUrl     // Tank listing endpoint
config.getWsUrlForTank(id)  // Get WS URL for specific tank
```

### Environment Variables

```bash
VITE_WS_URL=ws://localhost:8000     # WebSocket server
VITE_WS_PORT=8000                   # WebSocket port
VITE_API_URL=http://localhost:8000  # API server
VITE_API_PORT=8000                  # API port
```

## Development Notes

### Adding New Routes

Routes are defined in `App.tsx`:

```tsx
<Routes>
  <Route path="/" element={<HomePage />} />
  <Route path="/tank/:tankId" element={<TankPage />} />
  <Route path="/network" element={<NetworkDashboard />} />
</Routes>
```

### Tank-Aware Components

When creating components that need tank context:

```tsx
// In a route component
const { tankId } = useParams<{ tankId: string }>();
const { state, sendCommand } = useWebSocket(tankId);
```

### Rendering Performance

The Canvas renderer is optimized for 30+ FPS updates with hundreds of entities. Each entity type has a custom rendering function in `utils/renderer.ts`.

### Type Safety

All simulation data structures are typed in `types/simulation.ts`, matching the backend Pydantic models.

## Browser Compatibility

Requires a modern browser with:
- ES2020+ JavaScript support
- WebSocket support
- Canvas 2D API
- CSS Grid and Flexbox

## Future Enhancements

- [x] Multi-tank support (Tank World Net)
- [x] React Router navigation
- [x] Network dashboard
- [ ] Entity transfers between tanks
- [ ] Tank persistence/save/load
- [ ] D3.js graphs for trait evolution over time
- [ ] Zoom/pan controls for canvas
- [ ] Click on fish to see detailed info
- [ ] Speed controls (faster/slower simulation)
- [ ] Replay mode to watch evolution history
- [ ] Dark/light theme toggle
- [ ] Export statistics to CSV
