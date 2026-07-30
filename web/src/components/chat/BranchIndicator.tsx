import type { Message } from "@/types/chat";
import { GitFork } from "lucide-react";

export function BranchIndicator({ message }: { message: Message }) {
  return (
    <div className="flex justify-center my-2">
      <div className="text-[10px] text-[#8b8fa3] flex items-center gap-1 px-3 py-1 rounded-full border border-[#2a2d3a]">
        <GitFork size={12} /> {message.content}
      </div>
    </div>
  );
}
