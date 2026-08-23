import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function MarkdownRenderer({ content }: { content: string }) {
  if (!content) return null;
  return (
    <div className="prose prose-invert max-w-none text-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children }) {
            const isInline = !className;
            if (isInline) return <code className="bg-[#2a2d3a] px-1.5 py-0.5 rounded text-xs text-[#fbbf24]">{children}</code>;
            return <pre><code className={className}>{children}</code></pre>;
          },
        }}
      >{content}</ReactMarkdown>
    </div>
  );
}
