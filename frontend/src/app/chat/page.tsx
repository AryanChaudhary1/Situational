"use client";

import { useState, useEffect, useRef } from "react";
import { sendChatMessage, getChatHistory } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getChatHistory()
      .then((res) => {
        if (res?.data) setMessages(res.data.map((m: any) => ({ role: m.role, content: m.content })));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const res = await sendChatMessage(userMsg);
      if (res?.response) {
        setMessages((prev) => [...prev, { role: "assistant", content: res.response }]);
      }
    } catch (e: any) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${e.message}` }]);
    }
    setLoading(false);
  }

  return (
    <div className="flex flex-col h-[calc(100vh-48px)]">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-cyan-400">Chat</h1>
        <p className="text-gray-500 text-sm">Ask about markets, share news, or build investment theses</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-20">
            <p className="text-lg">Welcome to the Situation Room</p>
            <p className="text-sm mt-2">Try asking about current market conditions, a specific stock, or share a news article.</p>
            <div className="flex flex-wrap gap-2 justify-center mt-4">
              {["What's the current macro outlook?", "Analyze NVDA", "Is the yen carry trade unwinding?", "What are insiders buying?"].map((q) => (
                <button key={q} onClick={() => { setInput(q); }}
                  className="px-3 py-1.5 bg-[#1a1a2e] border border-gray-700 rounded-lg text-xs text-gray-300 hover:border-cyan-500 transition-colors">
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[75%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
              msg.role === "user"
                ? "bg-cyan-600 text-white"
                : "bg-[#1a1a2e] border border-gray-800 text-gray-200"
            }`}>
              <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#1a1a2e] border border-gray-800 rounded-xl px-4 py-3 text-sm text-gray-400">
              Analyzing...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2 pt-4 border-t border-gray-800">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about markets, share news, or describe a thesis..."
          className="flex-1 bg-[#1a1a2e] border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-colors"
          disabled={loading}
        />
        <button onClick={handleSend} disabled={loading || !input.trim()}
          className="px-6 py-3 bg-cyan-600 rounded-xl text-sm font-medium hover:bg-cyan-500 transition-colors disabled:opacity-50">
          Send
        </button>
      </div>
    </div>
  );
}
