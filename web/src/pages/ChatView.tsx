import { useEffect, useRef, useState } from "react";
import { ShieldAlert } from "lucide-react";
import { useParams } from "react-router-dom";
import { useChatStore } from "@/stores/chatStore";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { MessageList } from "@/components/chat/MessageList";
import { InputArea } from "@/components/chat/InputArea";

export function ChatView() {
  const { sessionId } = useParams();
  const [draft, setDraft] = useState("");
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const {
    selectSession, activeId, streaming, pendingApprovals, loadApprovals, decideApproval,
  } = useChatStore();

  useEffect(() => {
    if (sessionId && sessionId !== activeId) selectSession(sessionId);
  }, [sessionId, activeId, selectSession]);

  useEffect(() => {
    if (!activeId) return;
    void loadApprovals();
    if (!streaming && pendingApprovals.length === 0) return;
    const timer = window.setInterval(() => void loadApprovals(), 750);
    return () => window.clearInterval(timer);
  }, [streaming, activeId, pendingApprovals.length, loadApprovals]);

  return (
    <div className="flex flex-col h-full">
      <ChatHeader />
      <MessageList
        onSuggestion={(suggestion) => {
          setDraft(suggestion);
          composerRef.current?.focus();
        }}
      />
      <div aria-live="polite" className="mx-auto w-full max-w-4xl px-4 sm:px-6">
        {pendingApprovals.map((approval) => (
          <section key={approval.id} className="mb-3 rounded-xl border border-[#fbbf24]/40 bg-[#382b10] p-4 text-[#fde68a] shadow-lg">
            <div className="flex items-start gap-3">
              <ShieldAlert className="mt-0.5 shrink-0" size={20} aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <h2 className="text-sm font-semibold">允许调用受保护工具？</h2>
                <p className="mt-1 text-xs text-[#fde68a]">{approval.tool_name}</p>
                <pre className="mt-2 max-h-20 overflow-auto whitespace-pre-wrap break-words text-[11px] text-[#f4f4f5]">{approval.command}</pre>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" onClick={() => void decideApproval(approval.id, "approve")} className="min-h-9 rounded-lg bg-[#fbbf24] px-4 text-xs font-semibold text-black focus:outline-none focus:ring-2 focus:ring-white">
                    允许本次调用
                  </button>
                  <button type="button" onClick={() => void decideApproval(approval.id, "deny")} className="min-h-9 rounded-lg border border-[#fbbf24]/40 px-4 text-xs text-[#fde68a] hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-white">
                    拒绝
                  </button>
                </div>
              </div>
            </div>
          </section>
        ))}
      </div>
      <InputArea ref={composerRef} text={draft} onTextChange={setDraft} />
    </div>
  );
}
