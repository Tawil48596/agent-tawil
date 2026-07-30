import { useState } from "react";
import { Copy, Check } from "lucide-react";

export function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000); };

  return (
    <div className="my-2 rounded-lg overflow-hidden border border-[#2a2d3a]">
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#1a1d27] text-xs text-[#8b8fa3]">
        <span>{language || "code"}</span>
        <button onClick={handleCopy} className="hover:text-[#e1e4ea]">{copied ? <Check size={14} /> : <Copy size={14} />}</button>
      </div>
      <pre className="bg-[#0d1117] p-4 overflow-x-auto text-[13px] leading-relaxed"><code>{code}</code></pre>
    </div>
  );
}
