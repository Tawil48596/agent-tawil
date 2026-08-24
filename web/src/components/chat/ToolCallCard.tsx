import type { ToolCall } from "@/types/chat";

export function ToolCallCard({ call }: { call: ToolCall }) {
  return (
    <div className="mt-3 rounded-lg border border-white/10 bg-[#171717] px-3 py-2 font-mono text-xs text-[#d4d4d8]">
      <span className="font-semibold">🔧 {call.name}</span>
      <span className="ml-2 text-[#737373]">{call.status}</span>
      {call.result && <pre className="mt-1 text-[10px] text-[#4ade80] max-h-20 overflow-y-auto">{call.result}</pre>}
    </div>
  );
}
