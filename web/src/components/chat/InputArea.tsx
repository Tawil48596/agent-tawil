import { ChangeEvent, Dispatch, forwardRef, SetStateAction, useEffect, useRef, useState } from "react";
import { RotateCcw, Send, StopCircle, Paperclip } from "lucide-react";
import { useChatStore } from "@/stores/chatStore";

interface InputAreaProps {
  text: string;
  onTextChange: Dispatch<SetStateAction<string>>;
}

export const InputArea = forwardRef<HTMLTextAreaElement, InputAreaProps>(function InputArea(
  { text, onTextChange },
  composerRef,
) {
  const streaming = useChatStore((s) => s.streaming);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const stopStreaming = useChatStore((s) => s.stopStreaming);
  const retryLastMessage = useChatStore((s) => s.retryLastMessage);
  const interrupted = useChatStore((s) => s.interrupted);
  const fileRef = useRef<HTMLInputElement>(null);
  const [attachmentName, setAttachmentName] = useState("");

  useEffect(() => {
    if (!composerRef || typeof composerRef === "function" || !composerRef.current) return;
    composerRef.current.style.height = "0px";
    composerRef.current.style.height = `${Math.min(composerRef.current.scrollHeight, 176)}px`;
  }, [composerRef, text]);

  const attachFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > 1024 * 1024) {
      useChatStore.setState({ error: "附件不能超过 1 MB" });
      return;
    }
    try {
      const content = await file.text();
      onTextChange((current) => `${current}${current ? "\n\n" : ""}附件：${file.name}\n\`\`\`\n${content}\n\`\`\``);
      setAttachmentName(file.name);
    } catch {
      useChatStore.setState({ error: "当前仅支持文本类附件" });
    }
  };

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || streaming) return;
    onTextChange("");
    setAttachmentName("");
    void sendMessage(trimmed);
  };

  return (
    <div className="shrink-0 px-3 pb-3 pt-2 sm:px-6 sm:pb-5">
      <div className="mx-auto max-w-4xl rounded-2xl border border-white/10 bg-[#1b1b1b]/95 px-2 py-2 shadow-[0_16px_48px_rgba(0,0,0,.28)] backdrop-blur-xl transition focus-within:border-white/20 focus-within:ring-2 focus-within:ring-white/[0.07]">
        {attachmentName && (
          <div className="mx-2 mb-1 flex items-center gap-2 text-[11px] text-[#d4d4d8]">
            <Paperclip size={12} aria-hidden="true" />
            <span className="min-w-0 truncate">已附加 {attachmentName}</span>
          </div>
        )}
        <div className="flex gap-2 items-end">
          <input ref={fileRef} type="file" className="hidden" aria-label="选择文本附件"
          accept=".txt,.md,.json,.yaml,.yml,.toml,.csv,.py,.js,.jsx,.ts,.tsx,.css,.html,.go,.rs,.java"
          onChange={attachFile} />
          <button type="button" aria-label="添加文本附件" onClick={() => fileRef.current?.click()} className="mb-0.5 rounded-xl p-2.5 text-[#a3a3a3] transition hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50" title={attachmentName || "添加文本附件"}>
            <Paperclip size={18} aria-hidden="true" />
          </button>
          <textarea
          ref={composerRef}
          rows={1}
          aria-label="发送给 Agent 的消息"
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="描述你希望 Agent 完成的工作…"
          className="max-h-44 min-h-11 flex-1 resize-none bg-transparent px-2 py-3 text-sm leading-5 text-[#f4f4f5] outline-none placeholder:text-[#737373]"
          />
          {interrupted && !streaming && (
            <button
              type="button"
              onClick={() => retryLastMessage()}
              className="flex items-center gap-2 rounded-xl px-3 py-3 text-xs text-[#a3a3a3] transition hover:bg-white/5 hover:text-white"
              title="重新发送上一条消息"
            >
              <RotateCcw size={17} aria-hidden="true" /> <span className="hidden sm:inline">重新发送</span>
            </button>
          )}
          <button
            type="button"
            onClick={streaming ? stopStreaming : handleSend}
            disabled={!streaming && !text.trim()}
            title={streaming ? "停止生成" : "发送"}
            aria-label={streaming ? "停止生成" : "发送消息"}
            className="min-h-11 min-w-11 rounded-xl bg-[#f4f4f5] px-3 py-3 text-[#171717] shadow-sm transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
          >
            {streaming ? <StopCircle size={18} aria-hidden="true" /> : <Send size={18} aria-hidden="true" />}
          </button>
        </div>
      </div>
      <p className="mx-auto mt-2 max-w-4xl px-2 text-center text-[10px] text-[#666666]">Enter 发送 · Shift + Enter 换行 · 可随时停止并重新发送</p>
    </div>
  );
});
