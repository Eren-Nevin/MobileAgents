# Mate

A mobile-friendly web application for observing and controlling AI agents running in tmux sessions.

## Features

- **Real-time Monitoring**: Watch multiple AI agents across all tmux sessions, windows, and panes with live streaming updates
- **Input Detection**: Automatically detects when agents are waiting for user input (Claude Code, Codex, etc.)
- **Multiple Input Types**: Support for text input, choice selection, and confirmations
- **Mobile-First Design**: Optimized for mobile devices with responsive layouts and touch-friendly controls
- **WebSocket Streaming**: Real-time updates via tmux control mode with sub-20ms latency
- **Pane Filtering**: Filter panes by agent type (Claude, Codex) or view all
- **Flexible Views**: Toggle between session-grouped and grid layouts

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   tmux      │────▶│   Backend   │────▶│  Frontend   │
│  (sessions) │     │  (FastAPI)  │     │ (SvelteKit) │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │                   │                   │
  Control Mode      WebSocket Server      Real-time UI
  (streaming)       (broadcasting)        (reactive)
```

### Backend Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration via environment variables
│   ├── api/
│   │   ├── routes.py        # REST API endpoints
│   │   ├── websocket.py     # WebSocket handler
│   │   └── deps.py          # Dependency injection
│   ├── models/
│   │   ├── pane.py          # Pane state models
│   │   ├── input.py         # Input request models
│   │   └── events.py        # WebSocket event models
│   └── services/
│       ├── tmux.py          # tmux CLI wrapper
│       ├── registry.py      # Pane state storage
│       ├── parser.py        # Input request parser
│       ├── observer.py      # Background monitoring daemon
│       └── control_mode/    # tmux control mode implementation
├── tests/                   # pytest test suite
├── Dockerfile               # Production container
└── Dockerfile.dev           # Development container with hot reload
```

### Frontend Architecture

```
frontend/
├── src/
│   ├── routes/
│   │   ├── +page.svelte          # Home page (pane list)
│   │   └── pane/[id]/+page.svelte # Pane detail view
│   └── lib/
│       ├── api/
│       │   └── client.ts         # API client functions
│       ├── components/
│       │   ├── Header.svelte     # App header
│       │   ├── PaneList.svelte   # Pane listing with filters
│       │   ├── PaneCard.svelte   # Individual pane card
│       │   ├── PaneDetail.svelte # Full pane view with input
│       │   ├── PaneOutput.svelte # Terminal output display
│       │   └── InputBar.svelte   # Input controls
│       ├── stores/
│       │   └── panes.svelte.ts   # Reactive state management
│       └── types/
│           └── index.ts          # TypeScript definitions
├── Dockerfile                    # Production container
└── Dockerfile.dev                # Development container
```

## Requirements

- Python 3.11+
- Node.js 20+
- tmux 3.0+
- Docker & Docker Compose (optional)

## Quick Start

### Option 1: Docker with Host Network (Recommended for tmux access)

```bash
# Set your user/group IDs for proper tmux socket permissions
export HOST_UID=$(id -u)
export HOST_GID=$(id -g)

# Start with host network profile
docker compose -f docker-compose.dev.yml --profile hostnet up --build
```

Access at: http://localhost:5678

### Option 2: Local Development

```bash
# Terminal 1: Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8765

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

Access at: http://localhost:5173

### Option 3: Production Docker

```bash
docker compose up --build
```

Access at: http://localhost:4567

### Access URLs

| Setup | Frontend | Backend API | API Docs |
|-------|----------|-------------|----------|
| Local dev | http://localhost:5173 | http://localhost:8765 | http://localhost:8765/docs |
| Docker hostnet | http://localhost:5678 | http://localhost:8765 | http://localhost:8765/docs |
| Docker prod | http://localhost:4567 | http://localhost:8765 | http://localhost:8765/docs |

## API Reference

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/panes` | List all tracked panes |
| `GET` | `/api/panes/{id}` | Get specific pane details |
| `GET` | `/api/panes/{id}/output` | Get pane output (with optional `?refresh=true`) |
| `POST` | `/api/panes/{id}/input` | Send structured input (requires pane waiting) |
| `POST` | `/api/panes/{id}/keys` | Send raw keys to pane (always allowed) |
| `GET` | `/api/health` | Health check |

### WebSocket

Connect to `/ws` for real-time updates. Events:

```typescript
// Initial state on connect
{ "event": "initial_state", "panes": PaneInfo[] }

// Full state refresh
{ "event": "state", "panes": PaneInfo[] }

// Single pane update (most common)
{ "event": "pane_update", "pane_id": string, "status": string, "lines": string[], "input_request"?: InputRequest }

// New pane discovered
{ "event": "pane_discovered", "pane": PaneInfo }

// Pane removed
{ "event": "pane_removed", "pane_id": string }
```

### Input Submission

```bash
# Send text input
curl -X POST http://localhost:8765/api/panes/%0/input \
  -H "Content-Type: application/json" \
  -d '{"input_type": "text", "value": "my response"}'

# Send raw keys (no input request required)
curl -X POST http://localhost:8765/api/panes/%0/keys \
  -H "Content-Type: application/json" \
  -d '{"keys": "hello", "enter": true}'

# Send special keys
curl -X POST http://localhost:8765/api/panes/%0/keys \
  -H "Content-Type: application/json" \
  -d '{"keys": "Up", "enter": false, "literal": false}'
```

## Agent Input Protocol

Agents can emit structured prompts for rich input handling:

### Text Input
```
[INPUT_REQUIRED]
TYPE: text
PROMPT: Enter your name:
```

### Choice Input
```
[INPUT_REQUIRED]
TYPE: choice
OPTIONS:
1) Yes
2) No
3) Maybe
```

### Confirmation
```
[INPUT_REQUIRED]
TYPE: confirm
MESSAGE: Deploy to production?
```

## Configuration

Environment variables (prefix with `MATE_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `MATE_HOST` | `0.0.0.0` | Server bind address |
| `MATE_PORT` | `8000` | Server port |
| `MATE_DEBUG` | `false` | Enable debug logging |
| `MATE_CORS_ORIGINS` | `["*"]` | Allowed CORS origins (JSON array) |
| `MATE_POLL_INTERVAL` | `1.0` | Fallback polling interval (seconds) |
| `MATE_DISCOVERY_INTERVAL` | `5.0` | Pane discovery interval (seconds) |
| `MATE_CAPTURE_LINES` | `500` | Lines to capture per pane |
| `MATE_TMUX_SOCKET` | auto | Custom tmux socket path |

## Development

### Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

### Test Coverage

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Code Structure

Tests are organized by module:
- `test_parser.py` - Input request parsing
- `test_registry.py` - Pane state management
- `test_api.py` - REST API endpoints
- `test_observer.py` - Observer daemon
- `test_tmux.py` - tmux service wrapper

### Linting

```bash
# Backend
cd backend
ruff check .
mypy app/

# Frontend
cd frontend
npm run check
npm run lint
```

## Tech Stack

### Backend
- **FastAPI** - Modern async web framework
- **Uvicorn** - ASGI server
- **Pydantic v2** - Data validation
- **pytest** - Testing framework

### Frontend
- **SvelteKit 2** - Full-stack framework
- **Svelte 5** - Reactive UI with runes
- **Tailwind CSS 4** - Utility-first styling
- **TypeScript** - Type safety

## Troubleshooting

### tmux not found
Ensure tmux is installed and in PATH:
```bash
which tmux  # Should show path
tmux -V     # Should show version 3.0+
```

### Can't access host tmux from Docker
Use the `hostnet` profile which runs containers with host networking:
```bash
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker-compose.dev.yml --profile hostnet up
```

### WebSocket connection fails
Check CORS origins in backend config:
```bash
MATE_CORS_ORIGINS='["http://localhost:5678"]'
```

### Panes not showing
1. Verify tmux has running sessions: `tmux list-sessions`
2. Check backend logs for discovery errors
3. Ensure proper socket permissions with `HOST_UID`/`HOST_GID`

## License

AGPL-3.0-or-later

Commercial licenses are available for organizations that wish to use
this software without AGPL obligations. Contact: eren.m.nevin@gmail.com
