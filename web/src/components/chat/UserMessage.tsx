import type { Message } from "@/types/chat";

export function UserMessage({ message }: { message?: Message; content?: string }) {
  const text = message?.content || "";
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] px-4 py-3 rounded-xl text-sm bg-[#1a1d27]">
        <p>{text}</p>
      </div>
    </div>
  );
}
