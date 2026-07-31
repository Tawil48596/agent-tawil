export interface Session {
  id: string;
  title: string;
  source: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

export interface Message {
  id: number;
  session_id: string;
  role: "user" | "assistant" | "tool" | "system";
  content: string;
  tool_calls?: ToolCall[];
  token_count?: number;
  created_at: string;
}

export interface ToolCall {
  name: string;
  args: Record<string, any>;
  result?: string;
  status: "pending" | "running" | "done" | "error";
}

export interface SSEEvent {
  type: "text" | "thinking" | "tool_call" | "tool_calls" | "tool_result" | "tool_results" | "done" | "error";
  content?: string;
  message?: string;
  calls?: any[];
  results?: any[];
  usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
  model?: string;
}

export interface ToolDef {
  name: string;
  description: string;
  toolset: string;
  is_dangerous: boolean;
  tags: string[];
  genui_component?: string;
}

export interface ModelInfo {
  name: string;
  provider: string;
  available: boolean;
  context_length: number;
  supports_vision: boolean;
  supports_tools: boolean;
  supports_reasoning_effort?: boolean;
}
