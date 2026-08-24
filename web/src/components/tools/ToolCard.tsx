import type { ToolDef } from "@/types/chat";

export function ToolCard({ tool }: { tool: ToolDef }) {
  return (
    <div className="cursor-pointer rounded-xl border border-[#303030] bg-[#171717] p-4 transition-colors hover:border-white/25 hover:bg-[#1b1b1b]">
      <h3 className="font-semibold text-sm">{tool.name}</h3>
      <p className="text-xs text-[#8b8fa3] mt-1">{tool.description}</p>
      <div className="flex gap-1 mt-2 flex-wrap">
        {tool.tags?.map((tag: string) => <span key={tag} className="text-[10px] bg-[#2a2d3a] px-2 py-0.5 rounded">{tag}</span>)}
        {tool.is_dangerous && <span className="text-[10px] bg-[#3d1515] text-[#f87171] px-2 py-0.5 rounded">危险</span>}
      </div>
    </div>
  );
}
