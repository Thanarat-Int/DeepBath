# DeepBaht — Frontend (Next.js 16)

Chat UI for the DeepBaht multi-agent backend. Runs on port **4001**
(matches `docker-compose.yml`).

## Stack
- Next.js 16 (App Router, Turbopack default)
- React 19
- Tailwind CSS v4
- IBM Plex Sans Thai (Google Fonts) for proper Thai rendering

## Components
- [`ChatPanel`](components/ChatPanel.tsx) — message list + composer
- [`VoiceButton`](components/VoiceButton.tsx) — record audio → POST `/voice/transcribe` → fill composer
- [`AgentTracePanel`](components/AgentTracePanel.tsx) — shows the LangGraph agent path + per-node latency for the latest reply

## Local dev

```bash
# from repo root, ensure backend is up first:
docker compose up -d postgres backend mcp-server langfuse

# then run the frontend in another shell
cd frontend
npm install        # first time only
npm run dev        # → http://localhost:4001
```

## API contract

The frontend talks **directly** to the FastAPI backend at
`NEXT_PUBLIC_API_URL` (default `http://localhost:4000`). CORS is
allow-listed for `http://localhost:4001` in `backend/.env`.

| Endpoint | Used by |
|---|---|
| `POST /chat` | `ChatPanel` (every send) |
| `POST /voice/transcribe` | `VoiceButton` (after stop recording) |

Types in [`lib/types.ts`](lib/types.ts) mirror
`backend/app/schemas/chat.py` — keep them in lockstep.
