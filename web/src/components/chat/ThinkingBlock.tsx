import { useState } from "react";
import { ChevronDown, ChevronRight, Brain } from "lucide-react";

export function ThinkingBlock({ content }: { content: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="my-1">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1 text-xs text-[#737373] hover:text-[#e4e4e7]">
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <Brain size={14} /> 思考过程
      </button>
      {open && <div className="ml-1.5 mt-1 border-l border-[#303030] pl-6 text-xs italic text-[#a1a1aa]">{content}</div>}
    </div>
  );
}
