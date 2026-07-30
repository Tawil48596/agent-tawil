import { useParams } from "react-router-dom";
import { useChatStore } from "@/stores/chatStore";
import { Wrench, AlertTriangle } from "lucide-react";

export function ToolDetail() {
  const { toolName } = useParams();
  const tools = useChatStore((s) => s.tools);
  const tool = tools.find((t) => t.name === toolName);

  if (!tool) return <div className="p-6 text-[#8b8fa3]">工具未找到</div>;

  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-lg font-semibold flex items-center gap-2 mb-4"><Wrench size={20} /> {tool.name}</h2>
      <p className="text-sm text-[#8b8fa3] mb-4">{tool.description}</p>
      {tool.is_dangerous && (
        <div className="flex items-center gap-2 text-[#f87171] text-sm mb-4 bg-[#3d1515] px-4 py-2 rounded-lg">
          <AlertTriangle size={16} /> 危险工具 — 使用需审批
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {tool.tags?.map((t: string) => <span key={t} className="bg-[#2a2d3a] px-3 py-1 rounded text-xs">{t}</span>)}
      </div>
    </div>
  );
}
