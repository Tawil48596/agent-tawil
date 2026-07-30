import type { Message } from "@/types/chat";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import { ToolCallCard } from "./ToolCallCard";
import { CodeBlock } from "./CodeBlock";
import { ThinkingBlock } from "./ThinkingBlock";

export function AssistantMessage({ message, content }: { message?: Message; content?: string }) {
  const text = message?.content || content || "";
  const toolCalls = message?.tool_calls;

  // Split code blocks for Monaco-style rendering
  const parts = text.split(/(```\w*\n[\s\S]*?```)/g);

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] px-4 py-3 rounded-xl text-sm border border-[#2a2d3a] bg-[#0f1117]">
        {parts.map((part, i) => {
          if (part.startsWith("```")) {
            const lines = part.split("\n");
            const lang = lines[0].replace("```", "").trim();
            const code = lines.slice(1, -1).join("\n");
            return <CodeBlock key={i} code={code} language={lang} />;
          }
          return part ? <MarkdownRenderer key={i} content={part} /> : null;
        })}
        {toolCalls?.map((tc, i) => <ToolCallCard key={i} call={tc} />)}
      </div>
    </div>
  );
}
