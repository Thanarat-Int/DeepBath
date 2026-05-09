# 📚 DeepBaht — Complete Tech Stack Reference

Quick reference for every library, service, and tool that powers DeepBaht.
Use this as the answer to *"What tech do you use?"* in interviews or design
reviews — every choice has a one-line justification.

---

## 🧠 AI / ML Layer

| Tech | Role | Why we picked it |
|---|---|---|
| **Typhoon v2.5-30b-a3b-instruct** | Chat LLM (reasoning, generation) | Thai-native, OpenAI-compatible, free 200 RPM |
| **Typhoon ASR (`typhoon-asr-realtime`)** | Speech-to-text in Thai | Free 100 RPM, hosted (no GPU needed) |
| **bge-m3 (BAAI)** | Embeddings (1024-dim, multilingual) | Thai > OpenAI ada/3-small on MIRACL; self-host free |

---

## 🤖 GenAI Frameworks

| Tech | Role |
|---|---|
| **LangGraph 1.x** | Multi-agent orchestration (supervisor pattern) |
| **LangChain Core 1.x** | LLM abstraction + prompt templating |
| **LangChain OpenAI** | Typhoon integration (OpenAI-compatible API) |
| **PydanticOutputParser** | Structured JSON output (model-agnostic) |
| **LangFuse v4** | LLM observability + trace dashboard |
| **MCP Python SDK + FastMCP** | Streamable-HTTP MCP server |

---

## 🗄️ Backend

| Tech | Role |
|---|---|
| **FastAPI ≥0.115** | Async HTTP API + auto Swagger docs |
| **Uvicorn** | ASGI server |
| **Pydantic v2 + pydantic-settings** | Type-safe config + schemas |
| **SQLAlchemy 2.0 (async)** | ORM + Postgres connection pool |
| **asyncpg** | High-perf async Postgres driver |
| **sqlglot ≥25** | SQL AST parser (Text-to-SQL validator) |
| **httpx** | Async HTTP client (Typhoon ASR API) |
| **structlog** | Structured JSON logging |

---

## 🗄️ Database & Search

| Tech | Role |
|---|---|
| **PostgreSQL 16** | Primary DB (customers, accounts, transactions) |
| **pgvector 0.8** | Vector store inside the same Postgres (no separate service) |
| **HNSW index** | Approximate nearest neighbour search — O(log N) |
| **Read-only role (`deepbaht_ro`)** | Defense-in-depth for the Text-to-SQL agent |

---

## 🛡️ Security & Guardrails

| Tech | Role |
|---|---|
| **Custom Thai PII regex** | Citizen ID (Mod-11), bank account, phone, email |
| **Jailbreak phrase filter** | TH + EN substring match — blocked at middleware |
| **PydanticOutputParser** | Robust JSON output (no reliance on flaky tool-calling) |
| **CORS middleware** | Whitelist only the frontend origin |

---

## 🖥️ Frontend

| Tech | Role |
|---|---|
| **Next.js 16** | React framework (App Router + Turbopack) |
| **React 19** | UI library |
| **TypeScript 5+** | Type safety |
| **Tailwind CSS v4** | Utility-first styling |
| **IBM Plex Sans Thai** | Thai-friendly Google Font |
| **JetBrains Mono** | Monospace for code blocks |
| **MediaRecorder API** | Browser-native voice capture |

---

## 🐳 Containerisation & Infra

| Tech | Role |
|---|---|
| **Docker 29 + Buildx** | Multi-arch image builds, layer cache |
| **Docker Compose v5** | Local stack orchestration (5 services) |
| **Multi-stage Dockerfile** | Slim production images via `/opt/venv` pattern |
| **Healthchecks + `depends_on`** | Wait for Postgres before booting backend |

---

## 🚀 CI/CD & DevOps

| Tech | Role |
|---|---|
| **GitHub Actions** | CI/CD pipeline (lint + test + build + publish) |
| **GitHub Container Registry (GHCR)** | Image hosting (free for public packages) |
| **GHA layer cache** | Backend rebuild from ~10 min → ~30 sec |
| **Concurrency groups** | Cancel duplicate runs to save Action minutes |
| **Image tagging** | `:latest` + `:<sha7>` (best practice) |
| **Ruff** | Python linter + formatter (10× faster than flake8) |

---

## 🧪 Testing

| Tech | Role |
|---|---|
| **pytest ≥8.3** | Unit test runner |
| **pytest-asyncio** | Async test support |
| **44 unit tests** | chunker (5) + sql_safety (17) + guards (19) + health (3) |

---

## 📊 Observability

| Tech | Role | Status |
|---|---|---|
| **LangFuse v4 (self-hosted)** | LLM trace dashboard | Configured (export gated against v2 server) |
| **In-UI Agent Trace panel** | Per-turn timeline + latency | Live |
| **structlog (JSON)** | Production-ready logging | Live |

---

## 📚 Documentation & Presentation

| Tech | Role |
|---|---|
| **Markdown + GitHub** | All docs (README, demo-script, slides source) |
| **Marp CLI** | Render markdown → PDF slides |

---

## 🌐 Networking & Ports (4xxx range)

Deliberately out of the conventional 3000/5000/8000 ranges so DeepBaht doesn't
collide with anything else running on the same laptop.

| Port | Service |
|---|---|
| **4000** | Backend FastAPI |
| **4001** | Frontend Next.js |
| **4002** | LangFuse dashboard |
| **4432** | Postgres + pgvector (host port) |
| **4765** | MCP server |

---

# 🎯 One-page mental map

```
┌──────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                          │
│   Next.js 16 + React 19 + Tailwind v4 + IBM Plex Sans Thai       │
└─────────────────────────┬────────────────────────────────────────┘
                          │ HTTPS / fetch
┌─────────────────────────▼────────────────────────────────────────┐
│ BACKEND                                                           │
│   FastAPI + Pydantic v2 + SQLAlchemy 2 + structlog + httpx       │
│         │                                                         │
│   ┌─────▼─────────────────────────────────────────────┐          │
│   │  GUARDRAILS  Thai PII regex + Jailbreak filter    │          │
│   └─────┬─────────────────────────────────────────────┘          │
│         │                                                         │
│   ┌─────▼─────────────────────────────────────────────┐          │
│   │  AGENTS                                            │          │
│   │  LangGraph 1.x supervisor                          │          │
│   │    ├── RAG (bge-m3 + pgvector)                    │          │
│   │    ├── SQL (sqlglot validator + RO role)          │          │
│   │    └── MCP (FastMCP HTTP client)                  │          │
│   └─────┬─────────────────────────────────────────────┘          │
└─────────┼─────────────────────────────────────────────────────────┘
          │
    ┌─────┼──────┬─────────┬──────────┐
    ▼     ▼      ▼         ▼          ▼
 ┌─────┐ ┌──┐ ┌─────────┐ ┌──────┐ ┌──────────┐
 │Pg16+│ │MCP│ │ Typhoon │ │ ASR  │ │ LangFuse │
 │pgvec│ │HTTP│ │ LLM API │ │ API  │ │  Trace   │
 └─────┘ └──┘ └─────────┘ └──────┘ └──────────┘

─── INFRASTRUCTURE ──────────────────────────────────────────────────
Docker 29 + Compose v5 + Multi-stage Dockerfiles + Healthchecks

─── CI/CD ───────────────────────────────────────────────────────────
GitHub Actions (lint + test + build + publish to GHCR)
Ruff + pytest + GHA cache + Concurrency groups
```

---

# 🎙️ "Why X?" cheat sheet for interviews

| Question | Reply |
|---|---|
| Why Typhoon (not GPT-4o)? | Thai quality, OpenAI-compatible, sovereign data, free tier |
| Why bge-m3? | Multilingual, beats ada/3-small on Thai retrieval, self-host free |
| Why pgvector? | One DB for both policy embeddings and transactions → less ops |
| Why LangGraph? | Supervisor pattern is interpretable, cheaper than ReAct, easier to debug |
| Why PydanticOutputParser? | Typhoon's tool-calling isn't reliable → embed schema in prompt |
| Why sqlglot? | AST validator beats regex blocklists on edge cases |
| Why a read-only DB role? | Defence-in-depth — even a bypass of the validator fails at DB level |
| Why FastAPI async? | High throughput while waiting on LLM round-trips |
| Why Next.js 16? | App Router, Turbopack default, smallest bundle |
| Why Docker Compose? | Reproducible local stack, port-isolated for parallel projects |
| Why GHCR? | Free public registry that integrates with GitHub Actions out of the box |

---

# 🏆 Headline numbers

```
1 LLM (Typhoon)        · 3 specialist agents (RAG/SQL/MCP)
2 databases             · 5 docker services
4xxx port range         · 44 unit tests
20+ commits             · 4,200+ lines of code
3-day sprint            · ฿0 to run (free tiers + self-host)
```

---

# 📋 One-liner

> **Typhoon LLM + LangGraph multi-agent + bge-m3 RAG + pgvector + sqlglot
> SQL safety + FastAPI async + Next.js 16 + Docker Compose + GitHub Actions
> CI/CD + GHCR — entire stack runs on free tiers.**
