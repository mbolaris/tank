# Tank World Net - Phase 4 Planning Document

## Overview

Phase 4 builds on the solid foundation of Phases 2 and 3 by adding persistence, history tracking, and metadata management capabilities to Tank World Net. This phase focuses on making the network durable, observable, and user-friendly.

## Phase 4A: Persistence & History (Recommended First)

**Priority:** HIGH - Essential for production use
**Estimated Complexity:** Medium
**Dependencies:** None (builds on existing Phase 3 code)

### 1. Tank State Persistence

#### 1.1 Save Tank State to Disk

**Backend (`backend/tank_persistence.py`):**
```python
def save_tank_state(tank_id: str, manager: SimulationManager) -> str:
    """
    Save complete tank state to disk.

    Returns: filepath of saved state
    """
    - Serialize all entities (Fish, FractalPlant, Food, Nectar)
    - Save ecosystem statistics
    - Save tank metadata (name, description, settings)
    - Save RNG state for deterministic resume
    - Save current frame number
    - Create timestamped snapshot file
```

**File Format:**
```json
{
  "version": "1.0",
  "tank_id": "tank-abc123",
  "saved_at": "2025-11-24T20:30:00Z",
  "frame": 12345,
  "metadata": {
    "name": "Evolution Lab",
    "description": "Long-term evolution experiment",
    "allow_transfers": true,
    "seed": 42
  },
  "entities": [...],  // Serialized entities
  "ecosystem": {...}, // Statistics
  "rng_state": {...}  // Random state
}
```

**Storage Location:** `data/tanks/{tank_id}/snapshots/`

#### 1.2 Load Tank State from Disk

**API Endpoint:**
```
POST /api/tanks/load?file={snapshot_file}
```

**Features:**
- Validate snapshot file format
- Deserialize entities using existing `entity_transfer.py` logic
- Restore ecosystem statistics
- Resume from saved frame number
- Handle version migrations

#### 1.3 Auto-Save Feature

**Configuration:**
- Auto-save interval (default: 5 minutes)
- Max snapshots per tank (default: 10, rotating)
- Auto-save on tank stop/delete

**Implementation:**
- Background task per tank
- Non-blocking async saves
- Cleanup old snapshots based on retention policy

### 2. Transfer History Tracking

#### 2.1 Backend Transfer Log

**Model (`backend/models.py`):**
```python
@dataclass
class TransferRecord:
    transfer_id: str          # UUID
    timestamp: datetime
    entity_type: str          # "fish" or "fractal_plant"
    entity_old_id: int
    entity_new_id: int
    source_tank_id: str
    source_tank_name: str
    destination_tank_id: str
    destination_tank_name: str
    success: bool
    error: Optional[str] = None
```

**Storage:**
- In-memory circular buffer (last 100 transfers)
- Persistent log file: `data/transfers.log`
- Per-tank transfer count in metadata

**API Endpoint:**
```
GET /api/transfers?limit=50&tank_id={optional}
```

#### 2.2 Frontend Transfer History UI

**Component (`frontend/src/components/TransferHistory.tsx`):**

**Features:**
- Scrollable list of recent transfers
- Filter by tank (source/destination)
- Color-coded success/failure
- Entity type icons
- Timestamp display (relative: "2 min ago")
- Click to view tank details

**Layout:**
```
┌─────────────────────────────────────────┐
│ Transfer History                    [x] │
├─────────────────────────────────────────┤
│ 🐟 Fish #12345 → #67890                │
│ Lab A → Lab B                           │
│ ✓ Success • 2 min ago                   │
├─────────────────────────────────────────┤
│ 🌿 Plant #445 → #892                   │
│ Arena → Evolution                       │
│ ✗ Failed: Tank full • 5 min ago        │
└─────────────────────────────────────────┘
```

**Integration:**
- Add "History" button to Network Dashboard
- Show transfer count badge on tank cards
- Live updates via WebSocket event

### 3. Tank Metadata Management

#### 3.1 Update Tank Metadata API

**Endpoint:**
```
PATCH /api/tanks/{tank_id}/metadata
```

**Updatable Fields:**
- `name`: Tank display name
- `description`: Tank description
- `allow_transfers`: Toggle transfer permissions
- `is_public`: Public visibility
- `tags`: Array of category tags

**Frontend UI:**
- Edit button on tank card
- Modal with form fields
- Validation (name required, unique)
- Preview changes before applying

#### 3.2 Tank Tags/Categories

**Predefined Tags:**
- `evolution` - Evolution experiments
- `poker` - Poker game arenas
- `benchmark` - Performance testing
- `sandbox` - Experimental/playground
- `archive` - Long-term storage

**Features:**
- Filter tanks by tag in dashboard
- Tag-based color coding
- Tag statistics (count per tag)

### 4. Enhanced Dashboard Features

#### 4.1 Tank Search & Filter

**Search Bar:**
- Search by tank name/description
- Filter by status (running/paused/stopped)
- Filter by tag
- Sort by: name, fish count, generation, created date

#### 4.2 Bulk Operations

**Features:**
- Select multiple tanks (checkbox)
- Bulk pause/resume
- Bulk delete with confirmation
- Bulk tag assignment

#### 4.3 Tank Templates

**Predefined Templates:**
```python
TEMPLATES = {
    "evolution_lab": {
        "initial_fish": 20,
        "initial_plants": 10,
        "allow_transfers": True,
        "tags": ["evolution"]
    },
    "poker_arena": {
        "initial_fish": 8,
        "initial_plants": 5,
        "allow_transfers": False,
        "tags": ["poker"]
    }
}
```

**API:**
```
POST /api/tanks/from_template?template=evolution_lab&name=MyLab
```

---

## Phase 4B: Advanced Features (Future)

### 1. Cross-Tank Animations

**Visual Feedback:**
- Entity fades out from source tank thumbnail (1 sec)
- "Transferring..." indicator
- Entity fades into destination tank thumbnail (1 sec)
- Particle effect or trail animation

**Implementation:**
- WebSocket event: `{"type": "transfer_start", "entity_id": ...}`
- WebSocket event: `{"type": "transfer_complete", "entity_id": ...}`
- CSS transitions in Canvas renderer
- Coordinated timing across both tank views

### 2. Discovery & Remote Connections

#### 2.1 Central Registry Server

**Service:** Separate lightweight server for discovery
- Tank servers register themselves
- Clients query for available servers
- Health checks and pruning of stale entries

#### 2.2 Remote Tank Browsing

**Frontend:**
- "Add Server" dialog
- Browse remote tanks
- Connect to remote WebSocket
- Transfer between local and remote tanks

#### 2.3 Cross-Server Transfers

**Protocol:**
- Server-to-server API authentication
- Entity serialization over HTTP
- Async transfer with confirmation
- Network error handling and retry

### 3. Access Control & Security

#### 3.1 User Authentication

**Features:**
- User accounts with passwords
- API key authentication
- JWT tokens for session management

#### 3.2 Per-Tank Permissions

**Permission Levels:**
- `owner` - Full control (edit, delete, transfer)
- `collaborator` - Start/stop, transfer entities
- `viewer` - Read-only access

**Implementation:**
- Permission table: `tank_id → user_id → role`
- API middleware for permission checks
- Frontend UI shows only allowed actions

#### 3.3 Transfer Approval Workflow

**Features:**
- Destination tank owner approves incoming transfers
- Pending transfers queue
- Notification system
- Auto-approve option

### 4. Real-Time Collaboration

#### 4.1 Multi-User Chat

**Features:**
- Per-tank chat rooms
- Global network chat
- User presence indicators
- Chat history

#### 4.2 Shared Annotations

**Features:**
- Mark entities with notes
- Draw temporary shapes on canvas
- Collaborative planning tools

### 5. Analytics & Insights

#### 5.1 Cross-Tank Leaderboards

**Metrics:**
- Highest generation across all tanks
- Longest-lived fish
- Most successful genetic algorithm
- Most active tank (transfers in/out)

#### 5.2 Network Statistics Dashboard

**Visualizations:**
- Total fish/plants across network
- Transfer flow diagram (which tanks exchange most)
- Population trends over time
- Energy distribution heatmap

#### 5.3 Genetic Diversity Analysis

**Features:**
- Track genetic lineages across tanks
- Identify unique genomes
- Measure genetic diversity within/across tanks
- Suggest transfers to increase diversity

---

## Implementation Priority

### Phase 4A (Weeks 1-2)
1. ✅ Tank state persistence (save/load)
2. ✅ Transfer history logging
3. ✅ Metadata management UI
4. ✅ Auto-save feature

### Phase 4B (Weeks 3-4)
5. ⏸️ Cross-tank animations
6. ⏸️ Tank search & filter
7. ⏸️ Tank templates
8. ⏸️ Bulk operations

### Phase 4C (Future)
9. ⏸️ Discovery server
10. ⏸️ Remote connections
11. ⏸️ Access control
12. ⏸️ Analytics dashboard

---

## Technical Considerations

### Data Storage Strategy

**Option 1: JSON Files (Recommended for Phase 4A)**
- Simple, human-readable
- Easy backup/restore
- No database dependencies
- Good for <= 100 tanks

**Option 2: SQLite (Future)**
- Better performance at scale
- Query capabilities
- Transaction support
- Migration complexity

### WebSocket Event Extensions

**New Event Types:**
```json
{"type": "transfer_start", "entity_id": 123, "destination": "tank-xyz"}
{"type": "transfer_complete", "entity_id": 123, "new_id": 456}
{"type": "tank_saved", "tank_id": "tank-abc", "snapshot": "2025-11-24.json"}
{"type": "metadata_updated", "tank_id": "tank-abc", "field": "name"}
```

### Error Handling

**Persistence Errors:**
- Disk full → Show warning, skip auto-save
- Corrupt snapshot → Fall back to previous snapshot
- Load failure → Show error, allow manual recovery

**Transfer Errors:**
- Log all failures with stack traces
- Show user-friendly error messages
- Provide retry mechanism
- Preserve entity in source tank on failure

### Performance Optimization

**Lazy Loading:**
- Only load snapshots when needed
- Paginate transfer history (50 per page)
- Throttle auto-save writes

**Caching:**
- Cache tank metadata in memory
- Invalidate on update
- Reduce disk I/O

### Testing Requirements

**Unit Tests:**
- Serialization/deserialization roundtrip
- Snapshot file format validation
- Transfer history filtering

**Integration Tests:**
- Save → Stop → Load → Resume workflow
- Transfer with concurrent saves
- Metadata updates during active simulation

**End-to-End Tests:**
- User creates tank → saves → loads later
- Transfer entity → view in history
- Update metadata → verify persistence

---

## API Summary

### New Endpoints (Phase 4A)

```
POST   /api/tanks/{tank_id}/save                    # Save tank snapshot
POST   /api/tanks/load?file={snapshot}              # Load from snapshot
GET    /api/tanks/{tank_id}/snapshots               # List snapshots
DELETE /api/tanks/{tank_id}/snapshots/{snapshot_id} # Delete snapshot

GET    /api/transfers?limit=50&tank_id={id}         # Get transfer history
GET    /api/transfers/{transfer_id}                 # Get specific transfer

PATCH  /api/tanks/{tank_id}/metadata                # Update metadata
GET    /api/tags                                    # List all tags
```

### New Endpoints (Phase 4B)

```
GET    /api/tanks/templates                         # List templates
POST   /api/tanks/from_template?template={name}     # Create from template

GET    /api/discovery/servers                       # List registered servers
POST   /api/discovery/register                      # Register this server
```

---

## Success Metrics

### Phase 4A
- ✅ Tanks can be saved and restored without data loss
- ✅ Transfer history shows last 100 transfers
- ✅ Metadata can be updated via UI
- ✅ Auto-save runs every 5 minutes without performance impact

### Phase 4B
- ✅ Transfer animations are smooth and intuitive
- ✅ Users can find tanks via search in < 2 seconds
- ✅ Templates create properly configured tanks
- ✅ Bulk operations work on 10+ tanks simultaneously

### Long-Term Goals
- Support 100+ concurrent tanks per server
- Transfer success rate > 99.9%
- Dashboard load time < 1 second
- Zero data loss during crashes (recent auto-save)

---

## Migration Plan

### From Phase 3 to Phase 4A

**Backwards Compatibility:**
- Existing tanks continue to work without snapshots
- Transfer API unchanged (only adds history logging)
- Metadata updates are optional

**New Tank Defaults:**
```python
{
    "auto_save_enabled": True,
    "auto_save_interval": 300,  # 5 minutes
    "max_snapshots": 10,
    "tags": []
}
```

**Data Migration:**
- No migration needed (additive changes only)
- Snapshots created on-demand
- Transfer history starts from Phase 4A deployment

---

## Documentation Updates

### Files to Update
- ✅ `backend/README.md` - Add persistence and history endpoints
- ✅ `docs/ARCHITECTURE.md` - Add data storage section
- ✅ `docs/TANK_WORLD_NET_PHASE_4.md` - This document

### New Documentation
- `docs/PERSISTENCE.md` - Snapshot format specification
- `docs/TRANSFER_HISTORY.md` - History API and UI guide
- `docs/TANK_TEMPLATES.md` - Template creation guide

---

## Summary

Phase 4A provides essential production features:
- **Durability:** Save/load tank state, auto-save protection
- **Observability:** Transfer history and logging
- **Usability:** Metadata management and search

Phase 4B adds polish and advanced features:
- **Visual feedback:** Animations and transitions
- **Scalability:** Templates and bulk operations
- **Discovery:** Network-wide tank browsing

This phased approach allows incremental delivery while maintaining stability and backwards compatibility.
