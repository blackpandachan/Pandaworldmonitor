# Sentinel — Local Intelligence Platform

## What This Is
A local-first intelligence platform that aggregates global news, conflict data, natural events,
and infrastructure status into a unified situational awareness dashboard. Forked and refactored
from worldmonitor (https://github.com/koala73/worldmonitor).

## Architecture
- Backend: Python (FastAPI + FastMCP), SQLite, Gemini (3.1 Flash-Lite + 2.5 Flash)
- Frontend: React + Vite + MapLibre GL + Tailwind
- Communication: WebSocket for real-time updates, MCP for tool interaction

## Key Directories
- `sentinel/` — Python backend (MCP server, tools, analysis, pipeline)
- `frontend/` — React frontend
- `tests/` — Python test suite
- `sentinel/data/` — Static JSON data assets (feeds, bases, keywords, etc.)

## Running
```bash
uv run sentinel/main.py
```

## Environment
Copy `.env.example` to `.env` and fill in API keys.
Required: GEMINI_API_KEY (one key powers both models).
