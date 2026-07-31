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
  usage?: TokenUsage;
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
  usage?: TokenUsage;
  session_usage?: TokenUsage;
  model?: string;
}

export interface TokenUsage {
  input_tokens: number;
  cached_input_tokens: number;
  cache_write_input_tokens: number;
  output_tokens: number;
  reasoning_tokens: number;
  total_tokens: number;
  requests: number;
  cache_hit_rate?: number;
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
