# AutoX-SCB AI 🇹🇭🏦

> **Personal Finance Multi-Agent Assistant** powered by **Typhoon LLM** (SCB 10X) — an end-to-end GenAI system showcasing every capability listed in the SCB AI Engineer JD.

[![CI](https://github.com/USER/AutoX-Scb-AI/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-green)
![Docker](https://img.shields.io/badge/docker-ready-2496ED)

---

## ✨ Why this project?

This project is a deliberate, JD-driven demonstration of **end-to-end GenAI engineering** for a Thai banking context. Every architectural choice maps directly to a requirement in the role:

| JD Requirement | Implementation |
|---|---|
| End-to-End GenAI | Next.js → FastAPI → LangGraph → Postgres/pgvector → MCP, all containerised |
| Multi-Agent Orchestration | **LangGraph** supervisor pattern: `Supervisor → {RAG, SQL, MCP, Advisor}` |
| LLM Strategy | **Typhoon v2.5-30b** (chat) + **Typhoon v2.1-12b** (fast routing) — both via free OpenTyphoon API |
| Context Engineering | **RAG** (LlamaIndex + bge-m3 + pgvector) · **Text-to-SQL** · **MCP** server |
| Cloud Architecture | Docker Compose for local; deploy-ready for GCP Cloud Run / EKS |
| Monitoring & Guardrails | **LangFuse** self-hosted tracing · **Guardrails AI** (PII, jailbreak, hallucination) |
| App Dev | **Next.js 15** + shadcn/ui frontend, **FastAPI** async backend |
| DevOps | Multi-stage **Dockerfiles**, **GitHub Actions** CI, healthchecks |

---

## 🏛️ Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐
│  Next.js UI │───▶│ FastAPI GW   │───▶│ LangGraph           │
│ (chat+voice)│    │ + Guardrails │    │ Supervisor Agent    │
└─────────────┘    └──────────────┘    └─────────┬───────────┘
                          │                       │
                   ┌──────▼──────┐      ┌─────────┼─────────┐
                   │ Typhoon ASR │      ▼         ▼         ▼
                   │ (TH voice)  │  ┌──────┐ ┌────────┐ ┌──────────┐
                   └─────────────┘  │ RAG  │ │  SQL   │ │ MCP      │
                                    │Agent │ │ Agent  │ │ Agent    │
                                    └──┬───┘ └───┬────┘ └────┬─────┘
                                       ▼         ▼            ▼
                                  pgvector  PostgreSQL   Banking MCP
                                  (policy)  (txn data)   Server
                                       │
                              ┌────────▼────────┐
                              │ LangFuse Trace  │
                              └─────────────────┘
```

See [Architecture.md](Architecture.md) for the full diagram and [docs/](docs/) for design notes.

---

## 🎬 Demo Scenarios

| # | User says (TH) | Routes to | Showcases |
|---|---|---|---|
| 1 | "ค่าธรรมเนียมโอนเงินต่างประเทศคิดยังไง?" | RAG Agent | RAG over policy PDFs |
| 2 | "เดือนที่แล้วใช้เงินกับอาหารไปเท่าไหร่?" | SQL Agent | Text-to-SQL on transactions |
| 3 | "โอน 1,000 ให้แม่" | MCP Agent | MCP tool invocation |
| 4 | "เงินเดือน 50K ลงทุนอะไรดี?" | Supervisor → multi-step | Multi-agent reasoning |
| 5 | 🎤 *(speaks in Thai)* | Typhoon ASR → flow | Voice-first UX |

---

## 🚀 Quick Start

```bash
# 1. Set up environment
cp backend/.env.example backend/.env
# Edit backend/.env and add your TYPHOON_API_KEY (https://opentyphoon.ai)

# 2. Spin up everything (Postgres, pgvector, LangFuse, backend, frontend, MCP)
docker compose up --build

# 3. Open the app
open http://localhost:3000          # Next.js UI
open http://localhost:8000/docs     # FastAPI Swagger
open http://localhost:3001          # LangFuse dashboard
```

---

## 📁 Project Structure

```
AutoX-Scb-AI/
├── backend/             # FastAPI + LangGraph multi-agent system
│   ├── app/
│   │   ├── agents/      # LangGraph supervisor + worker agents
│   │   ├── core/        # config, LLM clients (Typhoon)
│   │   ├── guards/      # Guardrails AI integration
│   │   ├── monitoring/  # LangFuse hooks
│   │   ├── routers/     # /chat, /voice, /health
│   │   ├── services/    # RAG, ASR, SQL services
│   │   └── main.py
│   └── tests/
├── frontend/            # Next.js 15 chat UI
├── mcp-server/          # Custom Banking MCP server (transfers, balance, market)
├── data/
│   ├── policies/        # Sample SCB policy PDFs for RAG
│   └── seed/            # Postgres seed (transactions, users)
├── docs/                # Architecture, demo script, slide deck
├── .github/workflows/   # CI pipeline
└── docker-compose.yml
```

---

## 🛠️ Tech Stack Detail

**LLM & AI**: Typhoon 2 (chat/instruct) · Typhoon ASR (Thai speech) · bge-m3 (embeddings) · LangChain · LangGraph · LlamaIndex
**Backend**: FastAPI · Pydantic v2 · SQLAlchemy 2 · asyncpg · Alembic
**Frontend**: Next.js 15 (App Router) · React 19 · shadcn/ui · TanStack Query
**Data**: PostgreSQL 16 + pgvector · Redis (session)
**Observability**: LangFuse · OpenTelemetry · structlog
**Safety**: Guardrails AI · custom Thai PII regex
**Infra**: Docker · Docker Compose · GitHub Actions

---

## 📅 Build Timeline (3-day sprint)

- **Day 1** ✅ — Backend skeleton, LangGraph supervisor, **RAG + Text-to-SQL agents**, seed data
- **Day 2** — MCP server (HTTP transport), Guardrails (Presidio), LangFuse, Typhoon ASR
- **Day 3** — Next.js UI, CI/CD, end-to-end Docker test, slide deck, rehearsal

### Defense-in-depth highlights (Day 1)

- **RAG**: cite-or-refuse system prompt; bge-m3 multilingual embeddings; HNSW index
- **Text-to-SQL**: two-layer safety — `sqlglot` AST validator + Postgres `autox_ro` role with `SELECT`-only privileges; query is **shown back** to the user for trust

---

## 📝 License

MIT — built as a portfolio project for an SCB AI Engineer interview.

**Author**: Thanarat · engineersirigpt@gmail.com
