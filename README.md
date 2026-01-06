# Mate

A mobile-friendly web application for observing and controlling AI agents running in tmux sessions.

## Features

- **Real-time Monitoring**: Watch multiple AI agents across all tmux sessions, windows, and panes
- **Input Detection**: Automatically detects when agents are waiting for user input
- **Multiple Input Types**: Support for text input, choice selection, and confirmations
- **Mobile-First**: Designed for use on mobile devices
- **WebSocket Updates**: Live updates without polling

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   tmux      │────▶│   Backend   │────▶│  Frontend   │
│  (sessions) │     │  (FastAPI)  │     │ (SvelteKit) │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Requirements

- Python 3.11+
- Node.js 20+
- tmux
- Docker & Docker Compose (optional)

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Development with hot reloading
docker compose -f docker-compose.dev.yml up --build

# Production build
docker compose up --build

# Production with nginx reverse proxy
docker compose --profile production up --build
```

### Option 2: Local Development

```bash
# Run both backend and frontend
./scripts/dev.sh
```

Or run separately:

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Access

| Setup | Frontend | Backend API | API Docs |
|-------|----------|-------------|----------|
| Local dev | http://localhost:5173 | http://localhost:8765 | http://localhost:8765/docs |
| Docker dev | http://localhost:5678 | http://localhost:8765 | http://localhost:8765/docs |
| Docker prod | http://localhost:4567 | http://localhost:8765 | http://localhost:8765/docs |
| Docker + nginx | http://localhost | http://localhost/api | http://localhost:8765/docs |

## Agent Input Protocol

Agents must emit structured prompts when user input is required:

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

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/panes` | List all panes |
| GET | `/api/panes/{id}` | Get pane details |
| GET | `/api/panes/{id}/output` | Get pane output |
| POST | `/api/panes/{id}/input` | Send input to pane |
| WS | `/ws` | WebSocket for real-time updates |

## Configuration

Environment variables (prefix with `MATE_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `POLL_INTERVAL` | `1.0` | Seconds between output polls |
| `DISCOVERY_INTERVAL` | `5.0` | Seconds between pane discovery |
| `CAPTURE_LINES` | `500` | Lines to capture per pane |

## Project Structure

```
Mate/
├── backend/
│   ├── app/
│   │   ├── api/           # REST and WebSocket endpoints
│   │   ├── models/        # Pydantic models
│   │   └── services/      # Business logic
│   ├── tests/             # pytest tests
│   ├── Dockerfile         # Production Dockerfile
│   └── Dockerfile.dev     # Development Dockerfile
├── frontend/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api/       # API client
│   │   │   ├── components/ # Svelte components
│   │   │   ├── stores/    # Svelte stores
│   │   │   └── types/     # TypeScript types
│   │   └── routes/        # SvelteKit routes
│   ├── Dockerfile         # Production Dockerfile
│   └── Dockerfile.dev     # Development Dockerfile
├── scripts/
│   └── dev.sh             # Development script
├── docker-compose.yml     # Production compose
├── docker-compose.dev.yml # Development compose
└── nginx.conf             # Nginx reverse proxy config
```

## Tech Stack

### Backend
- FastAPI
- Uvicorn
- Pydantic v2

### Frontend
- SvelteKit 2
- Svelte 5 (with runes)
- Tailwind CSS 4
- TypeScript

## License

MIT
