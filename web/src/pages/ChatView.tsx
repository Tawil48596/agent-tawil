import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { useChatStore } from "@/stores/chatStore";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { MessageList } from "@/components/chat/MessageList";
import { InputArea } from "@/components/chat/InputArea";

export function ChatView() {
  const { sessionId } = useParams();
  const { selectSession, activeId } = useChatStore();

  useEffect(() => {
    if (sessionId && sessionId !== activeId) selectSession(sessionId);
  }, [sessionId]);

  return (
    <div className="flex flex-col h-full">
      <ChatHeader />
      <MessageList />
      <InputArea />
    </div>
  );
}
