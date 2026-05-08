# DeepBaht — Frontend

Next.js 15 chat UI with voice input. Bootstrapped on **Day 3** so we can
focus the first two days on the agentic backend.

## Plan (Day 3)

```bash
pnpm create next-app@latest . --ts --tailwind --app --eslint --use-pnpm
pnpm dlx shadcn@latest init
pnpm dlx shadcn@latest add button card input scroll-area dialog
```

Components:
- `ChatPanel`        — message list + composer
- `VoiceButton`      — record audio → POST /voice/transcribe → fill composer
- `AgentTraceDrawer` — live timeline of which agent ran (powered by `agent_path` + `traces`)
- `TraceLink`        — deep-link to LangFuse trace

Runs on **port 4001** locally (compose maps `4001:3000`).
