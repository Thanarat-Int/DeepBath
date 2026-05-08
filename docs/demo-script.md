# Demo Script — AutoX-SCB AI Interview Presentation

> ใช้สำหรับการนำเสนอวันสัมภาษณ์ที่ SCB ความยาว ~12 นาที + Q&A
> โทน: confident, technical, business-aware

---

## 1. Hook (30s)

> "สวัสดีครับ ผมธนรัตน์ ในช่วง 3 วันที่ผ่านมาผมสร้างระบบที่ชื่อว่า
> **AutoX-SCB AI** ขึ้นมาเป็น Personal Finance Multi-Agent Assistant
> ที่ใช้ **Typhoon LLM ของ SCB 10X** เป็นแกนหลัก และครอบคลุมทุก
> requirement ใน JD ของตำแหน่งนี้ครับ"

→ เปิดสไลด์ "JD requirement ↔ implementation matrix"

---

## 2. Problem framing (1 min)

> ลูกค้าธนาคารเจอ 3 pain points:
> 1. หา policy ในเว็บไม่เจอ → call center → รอนาน
> 2. อยากดูยอดใช้จ่ายแต่ต้อง export statement เอง
> 3. การให้คำปรึกษาการลงทุน scale ไม่ได้
>
> ระบบนี้ตอบโจทย์ทั้ง 3 ผ่าน Multi-Agent ตัวเดียวที่รับคำสั่งเป็น
> ภาษาไทย รองรับเสียง และทำ action ได้

---

## 3. Architecture walkthrough (2 min)

→ เปิด `Architecture.md`
- เน้น **LangGraph supervisor pattern** — agent คุย agent ผ่าน state
- เน้น **MCP** เป็น standard ที่ลด vendor lock-in
- เน้น **pgvector** ในตัว Postgres เดิม → ลด infrastructure cost

---

## 4. Live demo (5 min)

| Scenario | Type | Showcase |
|---|---|---|
| ค่าธรรมเนียมโอน USD ไป US? | Type | RAG (เปิด LangFuse trace) |
| เดือนนี้ใช้กับอาหารเท่าไหร่? | Type | Text-to-SQL (โชว์ generated SQL) |
| โอน 500 ให้บัญชีแม่ A3001 | Type | MCP tool call |
| ลงทุนยังไงดีรับเงิน 50K | 🎤 Voice | Typhoon ASR → Advisor → MCP (FX/quote) |

ทุก scenario โชว์ LangFuse trace + agent_path ใน UI

---

## 5. Engineering highlights (2 min)

1. **Typhoon-first** — ภาษาไทยดีกว่า GPT-4o ในหลาย benchmark + cost น้อยกว่า
2. **Guardrails ทุกชั้น** — input PII (Presidio + Thai regex) → routing classifier → output validator
3. **Observability** — LangFuse traces ทุก node + structured logs + OpenTelemetry
4. **Cost control** — fast model (8B) สำหรับ routing, chat model (70B) สำหรับ reasoning เท่านั้น
5. **Testable** — pytest + httpx async client + fixtures สำหรับ stubbed Typhoon

---

## 6. Production roadmap (1 min)

- Migrate Postgres → AlloyDB / Aurora
- Switch MCP transport stdio → streamable HTTP behind ALB
- Add Redis-backed short-term memory + LangGraph checkpointer
- Canary deploy via GitHub Actions → GKE
- A/B test prompts via LangFuse experiments

---

## 7. Q&A prep cheatsheet

| คำถามที่อาจโดน | คำตอบสั้น |
|---|---|
| ทำไมเลือก Typhoon ไม่ใช่ GPT-4o? | คุณภาพไทย, cost, sovereign data, และเป็น stack ของ SCB 10X |
| Hallucination จัดการยังไง? | RAG + citation enforcement + Guardrails output validator + low temperature |
| ถ้า MCP server ล่ม? | Circuit breaker (tenacity) + graceful fallback + supervisor reroute |
| Multi-tenant? | Session id → Postgres RLS + LangFuse user property |
| ใช้กับ regulated data ยังไง? | Self-host Typhoon on-prem (SCB cloud), Presidio masks PII before logging |
