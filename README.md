# Solospace - Multi-Agent AI Orchestration Platform

## Overview
Solospace is a multi-agent AI orchestration platform that enables users to solve complex problems by dynamically creating and coordinating specialized AI agents. It combines a visual workflow canvas with intelligent routing, real-time streaming, and support for dozens of LLM providers.

## Project Structure
```
solospace/
├── backend/                 # FastAPI Python backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI application entry point
│   │   ├── config.py       # Configuration settings
│   │   ├── database.py     # Async SQLite + ChromaDB setup
│   │   ├── models.py       # Pydantic & SQLAlchemy models
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── sessions.py # Session management endpoints
│   │   │   ├── agents.py   # Agent CRUD & execution
│   │   │   ├── chat.py     # Chat & SSE streaming
│   │   │   └── echohouse.py # Social simulation mode
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm_gateway.py      # Multi-provider AI gateway
│   │   │   ├── agent_executor.py   # ReAct agent execution
│   │   │   ├── planner.py          # DAG planning & topological sort
│   │   │   ├── router.py           # Smart auto-mode pre-router
│   │   │   ├── tools/              # Agent tools
│   │   │   │   ├── __init__.py
│   │   │   │   ├── web_search.py
│   │   │   │   ├── web_browser.py
│   │   │   │   ├── code_executor.py
│   │   │   │   ├── api_connector.py
│   │   │   │   └── memory.py
│   │   │   └── synthesizer.py      # Final response aggregation
│   │   ├── security/
│   │   │   ├── __init__.py
│   │   │   ├── ssrf_guard.py       # SSRF protection
│   │   │   └── jailbreak.py        # Prompt injection filter
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── embeddings.py       # Embedding utilities
│   │       └── context_window.py   # Smart context summarization
│   ├── requirements.txt
│   └── run.sh
├── frontend/                # Next.js 15 React frontend
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── canvas/         # Flow canvas page
│   │   ├── chat/           # Chat interface
│   │   └── echohouse/      # Social simulation
│   ├── components/
│   │   ├── FlowCanvas.tsx  # React Flow node editor
│   │   ├── AgentNode.tsx   # Custom agent node component
│   │   ├── ChatPanel.tsx   # Real-time chat with SSE
│   │   ├── ToolApprovalModal.tsx
│   │   └── ProviderSelector.tsx
│   ├── stores/
│   │   └── useAgentStore.ts # Zustand state management
│   ├── lib/
│   │   ├── api.ts          # API client
│   │   ├── websocket.ts    # WebSocket handler
│   │   └── crypto.ts       # AES-GCM encryption for API keys
│   ├── package.json
│   └── next.config.ts
└── README.md
```

## Core Features

### 1. Intelligent Request Routing (Smart Auto Mode)
- Semantic pre-router classifies queries as TRIVIAL, TOOL_USE, or COMPLEX
- Automatic agent team generation for complex tasks

### 2. Visual Agent Orchestrator (Flow Canvas)
- Node-based editor with drag-and-drop connections
- Auto-layout with Dagre, minimap, zoom/pan
- Real-time agent status and tool logs

### 3. Multi-Provider AI Gateway
- Support for 20+ LLM providers (Gemini, OpenAI, Claude, Groq, Ollama, etc.)
- Streaming, JSON mode, automatic fallback

### 4. Agent Toolset
- Web Search, Web Browser, Code Executor, API Connector
- Memory via ChromaDB vector store
- Inter-agent messaging

### 5. Real-time Execution & Approval
- SSE streaming for agent thoughts and tool calls
- Tool approval modals via WebSocket

### 6. Persistence & Session Management
- Async SQLite for sessions, checkpoints, approvals
- WebSocket state sync
- Encrypted client-side API key storage

### 7. EchoHouse – Social Simulation Mode
- Generate character casts for interpersonal reflection
- Multi-round conversation simulation
- Therapeutic insight synthesis

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Architecture

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 15, React 19, Zustand, React Flow |
| Backend | FastAPI (Python 3.11+), Uvicorn |
| Database | aiosqlite + ChromaDB |
| Streaming | SSE + WebSocket |
| Security | SSRF guard, sandboxed code execution |
| Encryption | Web Crypto API (AES-GCM 256) |

## License
MIT
