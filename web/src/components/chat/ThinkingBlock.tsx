import { useState } from "react";
import { ChevronDown, ChevronRight, Brain } from "lucide-react";

export function ThinkingBlock({ content }: { content: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="my-1">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1 text-xs text-[#8b8fa3] hover:text-[#e1e4ea]">
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <Brain size={14} /> 思考过程
      </button>
      {open && <div className="mt-1 pl-6 text-xs text-[#8b8fa3] italic border-l border-[#2a2d3a] ml-1.5">{content}</div>}
    </div>
  );
}
