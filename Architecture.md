┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐
│  Next.js UI │───▶│ FastAPI GW   │───▶│ LangGraph           │
│ (chat+voice)│    │ + Guardrails │    │ Supervisor Agent    │
└─────────────┘    └──────────────┘    └─────────┬───────────┘
                          │                       │
                   ┌──────▼──────┐                │
                   │ Typhoon ASR │      ┌─────────┼─────────┐
                   │ (TH voice)  │      ▼         ▼         ▼
                   └─────────────┘  ┌──────┐ ┌────────┐ ┌──────────┐
                                    │ RAG  │ │  SQL   │ │ MCP      │
                                    │Agent │ │ Agent  │ │ Agent    │
                                    └──┬───┘ └───┬────┘ └────┬─────┘
                                       ▼         ▼            ▼
                                  pgvector  PostgreSQL   Banking MCP
                                  (policy)  (txn data)   Server
                                       │
                              ┌────────▼────────┐
                              │ LangFuse Trace  │
                              └─────────────────┘
