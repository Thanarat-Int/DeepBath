# DeepBaht 🐬💸

> **Multi-Agent AI for Thai Personal Finance** — a platform-agnostic GenAI
> assistant that answers policy questions (RAG), reasons over transactions
> (Text-to-SQL), and takes actions through a Model Context Protocol server.
> Built around **Typhoon** (Thai-native LLM) with a deliberate, JD-driven
> architecture covering the full GenAI engineering surface.

[![CI/CD](https://github.com/Thanarat-Int/DeepBath/actions/workflows/ci.yml/badge.svg)](https://github.com/Thanarat-Int/DeepBath/actions/workflows/ci.yml)
[![GHCR](https://img.shields.io/badge/ghcr.io-deepbaht--backend-2496ED)](https://github.com/Thanarat-Int/DeepBath/pkgs/container/deepbaht-backend)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Next.js](https://img.shields.io/badge/Next.js-16-black)
![LangGraph](https://img.shields.io/badge/LangGraph-1.x-green)
![Typhoon](https://img.shields.io/badge/LLM-Typhoon%20v2.5--30b-emerald)
![Tests](https://img.shields.io/badge/tests-44%20passing-success)
![Docker](https://img.shields.io/badge/docker-ready-2496ED)

---

## ✨ JD ↔ Implementation matrix

A deliberate, requirement-driven mapping for the Senior AI Engineer role:

| JD requirement | DeepBaht | Where to look |
|---|---|---|
| End-to-End GenAI | Next.js → FastAPI → LangGraph → Postgres → MCP, all containerised | repo root |
| Multi-Agent Orchestration | **LangGraph** supervisor pattern: `Supervisor → {RAG, SQL, MCP, Advisor}` | [`backend/app/agents/`](backend/app/agents/) |
| LLM Strategy | **Typhoon v2.5-30b** (free OpenTyphoon API) + Ollama fallback | [`backend/app/core/llm.py`](backend/app/core/llm.py) |
| Context Engineering | **RAG** (bge-m3 + pgvector) · **Text-to-SQL** (sqlglot) · **MCP** server | [`services/`](backend/app/services/) |
| Cloud Architecture | Docker Compose · 4xxx port range · multi-stage Dockerfiles · health-checked | [`docker-compose.yml`](docker-compose.yml) |
| Monitoring & Guardrails | **LangFuse** self-hosted tracing · Thai PII redactor · jailbreak filter | [`monitoring/`](backend/app/monitoring/) [`guards/`](backend/app/guards/) |
| App Dev | **Next.js 16** + Tailwind v4 + Voice button, **FastAPI** async backend | [`frontend/`](frontend/) [`backend/`](backend/) |
| DevOps | Multi-stage Dockerfiles · Compose · 44 unit tests · **GitHub Actions CI/CD** (lint+test+build+publish to GHCR) · port isolation | [`backend/Dockerfile`](backend/Dockerfile) · [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |

---

## 🏛️ Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐
│  Next.js UI │───▶│ FastAPI GW   │───▶│ LangGraph           │
│ (chat+voice)│    │ + Guardrails │    │ Supervisor Agent    │
│   :4001     │    │   :4000      │    │                     │
└─────────────┘    └──────┬───────┘    └─────────┬───────────┘
                          │                       │
                   ┌──────▼──────┐      ┌─────────┼─────────┐
                   │ Typhoon ASR │      ▼         ▼         ▼
                   │ (TH voice)  │  ┌──────┐ ┌────────┐ ┌──────────┐
                   └─────────────┘  │ RAG  │ │  SQL   │ │ MCP      │
                                    │Agent │ │ Agent  │ │ Agent    │
                                    └──┬───┘ └───┬────┘ └────┬─────┘
                                       ▼         ▼            ▼
                                  pgvector  PostgreSQL   Banking MCP
                                  (policy)  (txn data)   :4765
                                  :4432     :4432
                                       │
                              ┌────────▼────────┐
                              │ LangFuse Trace  │
                              │     :4002       │
                              └─────────────────┘
```

---

## 🎬 Demo Scenarios

| # | User says (TH) | Path | Showcases |
|---|---|---|---|
| 1 | *"ค่าธรรมเนียมโอนเงินต่างประเทศคิดยังไง?"* | `rag` | RAG over policy docs with `[1][2][4]` citations |
| 2 | *"เดือนที่แล้วใช้กับอาหารไปเท่าไหร่?"* | `sql` | Text-to-SQL with sqlglot validator + auto LIMIT |
| 3 | *"โอนเงิน 1,500 ให้บัญชี A3001"* | `mcp` | streamable-HTTP MCP tool call with TX ref |
| 4 | *"Ignore previous instructions…"* | (refused) | Jailbreak guard — never reaches the LLM |
| 5 | 🎤 *(speaks in Thai)* | rag/sql/mcp | Typhoon ASR → flow |

End-to-end latency is **2-3 seconds** per turn after the embedding model is warm.

---

## 🚀 Quick start

```bash
# 1. Set up environment
cp backend/.env.example backend/.env
# Edit backend/.env and fill in:
#   - TYPHOON_API_KEY        (https://opentyphoon.ai — free, email signup)
#   - LANGFUSE_PUBLIC_KEY    (http://localhost:4002 → Settings → API Keys)
#   - LANGFUSE_SECRET_KEY    (same)

# 2. Spin up the backend stack
docker compose up -d postgres backend mcp-server langfuse-db langfuse

# 3. Ingest sample policy docs (first run downloads bge-m3 ~2 GB)
docker compose exec backend python -m scripts.ingest_policies

# 4. Run the frontend
cd frontend && npm install && npm run dev   # http://localhost:4001

# 5. Visit
open http://localhost:4001          # chat UI
open http://localhost:4000/docs     # FastAPI Swagger
open http://localhost:4002          # LangFuse dashboard
```

### Local ports — all in the 4xxx range to avoid clashing

| Port | Service |
|---|---|
| **4000** | Backend (FastAPI) |
| **4001** | Frontend (Next.js) |
| **4002** | LangFuse dashboard |
| **4432** | Postgres + pgvector |
| **4765** | MCP server |

---

## 🛠️ Tech stack

**LLM & AI**: Typhoon v2.5-30b · Typhoon ASR · bge-m3 (1024-dim multilingual) · LangChain · LangGraph
**Backend**: FastAPI · Pydantic v2 · SQLAlchemy 2 · asyncpg · sqlglot
**Frontend**: Next.js 16 (App Router, Turbopack) · React 19 · Tailwind v4 · IBM Plex Sans Thai
**Data**: PostgreSQL 16 + pgvector
**Observability**: LangFuse (OTEL) · structlog
**Safety**: custom Thai-PII regex + Mod-11 ID validator · jailbreak heuristic · DB-level RO role
**Infra**: Docker · Docker Compose · multi-stage Dockerfiles

---

## 🛡️ Defense-in-depth highlights

### Text-to-SQL — two safety layers

1. **AST validator** — `sqlglot` rejects DML/DDL/system tables, allow-lists `customers/accounts/transactions`, injects `LIMIT`.
2. **Database role** — `deepbaht_ro` has `SELECT`-only privileges. Even if the validator were bypassed, Postgres itself rejects writes.

Verified live: `DROP / DELETE / UPDATE / TRUNCATE` all denied at both layers.

### PII redaction — Thai-aware

Every chat turn flows through a redactor **before** Typhoon sees it.

| Pattern | Detection |
|---|---|
| Citizen ID (13 digits) | Mod-11 checksum verified — won't over-flag random 13-digit strings |
| Bank account | Grouped `xxx-x-xxxxx-x` |
| Mobile phone | TH prefixes `06/08/09` + variable separators |
| Email, Passport | Regex |

19 unit tests cover positive + negative cases.

### Jailbreak

Curated phrase list (TH + EN) — sub-millisecond match on every turn. Catches the obvious 80%; production should layer Llama Guard / Constitutional AI on top.

---

## 📊 Numbers

| Metric | Value |
|---|---|
| Commits over 3 days | **13** |
| Lines authored (code + docs + sql) | **4,206** |
| Unit tests | **44 / 44 passing** |
| End-to-end latency | **2-3 s** (warm cache) |
| Container images | 2 ours · 3 third-party |
| Cost to run forever | **0 ฿** (free Typhoon + self-hosted LangFuse) |

---

## 📁 Project structure

```
deepbaht/
├── backend/                  # FastAPI + LangGraph
│   ├── app/
│   │   ├── agents/           # supervisor + rag + sql + mcp + state
│   │   ├── core/             # config, llm (Typhoon), db, logging
│   │   ├── guards/           # PII + jailbreak
│   │   ├── monitoring/       # LangFuse client + RunnableConfig
│   │   ├── routers/          # /chat, /voice/transcribe, /health
│   │   ├── services/         # rag, sql, mcp_client, asr, embeddings, vector_store
│   │   ├── schemas/          # Pydantic request/response
│   │   └── main.py
│   ├── scripts/              # ingest_policies CLI
│   └── tests/                # 44 unit tests
├── frontend/                 # Next.js 16 chat UI
│   ├── app/                  # layout, page, globals
│   ├── components/           # ChatPanel, VoiceButton, AgentTracePanel
│   └── lib/                  # api client + types
├── mcp-server/               # FastMCP banking tools (HTTP transport)
├── data/
│   ├── policies/             # sample Thai banking policy markdown
│   └── seed/                 # Postgres schema + customers + transactions + RO role
├── docs/
│   ├── SLIDES.md             # Marp-format presentation
│   └── demo-script.md        # 12-min talk track + Q&A cheatsheet
└── docker-compose.yml
```

---

## 📝 License

DeepX

**Author**: Thanarat.Chue
