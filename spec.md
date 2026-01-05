# tmux Agent Web Observer & Control App — Specification

## 1. Purpose

Build a **mobile-friendly web application** that allows a user to:

- Observe what multiple AI agents (Codex or other CLI agents) are doing
- Across **all tmux sessions, windows, and panes**
- In near real-time
- Detect when agents are waiting for input
- Respond to agents from the web UI
  - Free-text input
  - Choice / menu selection
  - Confirmation actions

The system acts as an **agent supervisor / control plane** on top of tmux.

---

## 2. Non‑Goals

- Not a terminal emulator
- Not screen scraping or VT parsing
- Not agent-specific (Codex, Claude, etc. are interchangeable)
- Not a full auth/permissions product (basic auth only in v1)

---

## 3. High‑Level Architecture

```
+--------------------+
| tmux               |
|  sessions/windows  |
|   panes (agents)   |
+----------+---------+
           |
           | capture-pane / send-keys
           v
+--------------------+
| Observer Daemon    |
|  (Python)          |
|  - pane discovery  |
|  - output diffing  |
|  - input detection |
+----------+---------+
           |
           | events
           v
+--------------------+
| Backend API        |
|  FastAPI           |
|  WebSockets        |
|  State registry    |
+----------+---------+
           |
           | JSON / WS
           v
+--------------------+
| Web App (PWA)      |
|  - mobile-first    |
|  - live panes      |
|  - input controls  |
+--------------------+
```

---

## 4. tmux Interaction Model

### 4.1 Pane Discovery

The system must enumerate tmux structure periodically:

- Sessions
- Windows per session
- Panes per window

Commands used:

```bash
tmux list-sessions
tmux list-windows -t <session>
tmux list-panes -t <session>:<window> -F "#{pane_id} #{pane_title}"
```

Each pane is uniquely identified by `pane_id` (e.g. `%3`).

---

### 4.2 Output Capture

Pane output is captured using:

```bash
tmux capture-pane -p -t <pane_id> -S -<N>
```

Rules:
- Capture last N lines (default 500–1000)
- Poll every 500–1000 ms
- Diff against previous capture to extract only new lines
- Do **not** rely on terminal control sequences

Each pane maintains:
- last_hash
- last_seen_line
- rolling buffer (for UI)

---

### 4.3 Input Injection

All agent input is injected using:

```bash
tmux send-keys -t <pane_id> "<input>" Enter
```

Constraints:
- Only allow injection when pane is marked `waiting_input`
- Log every injected input with timestamp

---

## 5. Agent Input Protocol (Critical)

Agents **must emit structured prompts** when user input is required.

### 5.1 Required Marker

All input requests must include:

```
[INPUT_REQUIRED]
```

---

### 5.2 Input Types

#### 5.2.1 Text Input

```
[INPUT_REQUIRED]
TYPE: text
PROMPT: Enter max leverage:
```

#### 5.2.2 Choice / Menu

```
[INPUT_REQUIRED]
TYPE: choice
OPTIONS:
1) Yes
2) No
3) Explain more
```

#### 5.2.3 Confirmation

```
[INPUT_REQUIRED]
TYPE: confirm
MESSAGE: Deploy to production?
```

---

### 5.3 Observer Parsing Output

The observer daemon must parse pane output and emit structured state:

```json
{
  "pane_id": "%3",
  "status": "waiting_input",
  "input_type": "choice",
  "prompt": "Deploy to production?",
  "options": ["Yes", "No", "Explain more"]
}
```

---

## 6. Observer Daemon (Python)

### Responsibilities

- Discover tmux panes
- Poll pane output
- Detect `[INPUT_REQUIRED]` blocks
- Track pane state:
  - running
  - waiting_input
  - idle
  - exited
- Emit events to backend

### Internal State (per pane)

```python
PaneState:
  pane_id: str
  session: str
  window: str
  title: str
  status: str
  last_output_hash: str
  last_lines: list[str]
  input_request: dict | None
```

---

## 7. Backend API (FastAPI)

### Core Responsibilities

- Maintain authoritative pane registry
- Serve pane metadata and output
- Handle input injection requests
- Broadcast updates via WebSockets

---

### REST Endpoints

```
GET  /panes
GET  /panes/{pane_id}
GET  /panes/{pane_id}/output
POST /panes/{pane_id}/input
```

#### POST /panes/{pane_id}/input

```json
{
  "type": "text",
  "value": "yes"
}
```

Backend validates:
- pane exists
- pane is waiting_input
- input type matches request

---

### WebSocket

```
/ws
```

Events:

```json
{
  "event": "pane_update",
  "pane_id": "%3",
  "status": "waiting_input",
  "lines": ["..."]
}
```

---

## 8. Web App (PWA)

### Design Goals

- Mobile-first
- Readable logs
- Low cognitive load
- Explicit agent control

---

### Core Views

#### 8.1 Pane List

- Session / window grouping
- Pane title
- Status indicator
  - 🟢 running
  - 🟡 waiting input
  - 🔴 exited

#### 8.2 Pane Detail View

- Scrollable output log
- Sticky input area when required

---

### Input UI Mapping

| Input Type | UI Element |
|---------|------------|
| text | Text input + Send |
| choice | Buttons per option |
| confirm | Approve / Cancel |

---

## 9. Security (v1)

- FastAPI binds to localhost
- Exposed via reverse proxy (Caddy/Nginx)
- Basic auth or JWT
- HTTPS only

---

## 10. Operational Considerations

- Observer runs as a daemon (systemd or tmux)
- Backend restarts must not break tmux
- Pane discovery is idempotent
- UI tolerates temporary disconnects

---

## 11. Implementation Phases

### Phase 1 — MVP
- Pane discovery
- Output polling
- Text input injection
- Simple web UI

### Phase 2 — Interaction
- Input protocol parsing
- Choice & confirm UI
- WebSocket streaming

### Phase 3 — Power User
- Agent summaries
- Notifications
- Read-only vs write mode
- Audit logs

---

## 12. Design Principles

- tmux is the source of truth
- Agents remain CLI-native
- Web UI is a control surface, not execution layer
- Explicit over implicit
- Observable > interactive > automated

---

## 13. Future Extensions (Out of Scope)

- Agent scheduling
- Persistent agent memory
- Multi-user RBAC
- Cloud-hosted version
- Plugin system

---

**This spec is intended to be handed directly to Codex or other agent-based developers to implement the system end-to-end.**

