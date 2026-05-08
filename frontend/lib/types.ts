// Shared types — mirror the FastAPI Pydantic schemas in backend/app/schemas/chat.py.
// Keeping these in lockstep is what TypeScript buys us; if the backend evolves,
// the compiler will yell here first.

export type Role = "user" | "assistant" | "system" | "tool";
export type AgentName = "supervisor" | "rag" | "sql" | "mcp" | "advisor";

export interface ChatMessage {
  role: Role;
  content: string;
  agent?: AgentName | null;
}

export interface AgentTrace {
  agent: AgentName;
  input: string;
  output: string;
  tokens_in: number;
  tokens_out: number;
  latency_ms: number;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  agent_path: AgentName[];
  traces: AgentTrace[];
  finished_at: string;
}

export interface TranscriptionResponse {
  text: string;
  duration_s: number | null;
  language: string;
}

// Local UI state — distinct from the wire types above.
export interface UiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent_path?: AgentName[];
  traces?: AgentTrace[];
  pending?: boolean;
}
