import type { Message } from "@/types/chat";

export function UserMessage({ message }: { message?: Message; content?: string }) {
  const text = message?.content || "";
  return (
    <div className="mx-auto flex w-full max-w-3xl justify-end">
      <div className="max-w-[85%] rounded-2xl border border-white/[0.07] bg-[#242424] px-4 py-3 text-sm leading-6 text-[#f4f4f5] shadow-sm">
        <p className="whitespace-pre-wrap">{text}</p>
      </div>
    </div>
  );
}
