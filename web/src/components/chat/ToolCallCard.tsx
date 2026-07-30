import type { ToolCall } from "@/types/chat";

export function ToolCallCard({ call }: { call: ToolCall }) {
  return (
    <div className="bg-[#1e2030] border border-[#fbbf24] text-[#fbbf24] px-3 py-2 rounded-lg text-xs font-mono mt-2">
      <span className="font-semibold">🔧 {call.name}</span>
      <span className="text-[#8b8fa3] ml-2">{call.status}</span>
      {call.result && <pre className="mt-1 text-[10px] text-[#4ade80] max-h-20 overflow-y-auto">{call.result}</pre>}
    </div>
  );
}
