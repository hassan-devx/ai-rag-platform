"use client";
import React, { useState, useRef, useEffect } from "react";

export default function UserAgentDashboard() {
  const [messages, setMessages] = useState([
    { 
      role: "assistant", 
      content: "Hello! I am your autonomous assistant. I can search internal project archives or run live web lookups to answer your questions accurately. How can I help you today?" 
    }
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scrolls the chat window to the newest chunks as they stream in
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userPrompt = input;
    setInput("");
    
    // 1. Append the user's message to the feed
    setMessages((prev) => [...prev, { role: "user", content: userPrompt }]);
    setIsStreaming(true);

    // 2. Append a placeholder message for the assistant stream
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      // Pointing directly to your backend agent loop
      const response = await fetch("http://127.0.0.1:8000/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: userPrompt }),
      });

      if (!response.body) {
        throw new Error("No readable stream response returned from backend.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let compiledResponse = "";

      // 3. Process the streaming chunks from FastAPI dynamically
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const textChunk = decoder.decode(value, { stream: true });
        compiledResponse += textChunk;

        // Overwrite the final message item with the accumulating text stream
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1].content = compiledResponse;
          return updated;
        });
      }
    } catch (error) {
      console.error("Agent network connection error:", error);
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1].content = "⚠️ Failed to establish a streaming connection to the agent backend service. Please check your server status.";
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100 font-sans antialiased">
      {/* Structural Workspace Sidebar */}
      <div className="w-64 bg-slate-950 border-r border-slate-800 p-5 flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <h1 className="text-md font-bold tracking-wide uppercase text-slate-300">
              Agent Core
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">Autonomous Execution Mode</p>
          
          <nav className="mt-8 space-y-2">
            <div className="px-3 py-2 text-xs font-medium text-emerald-400 bg-emerald-950/40 rounded-md border border-emerald-900/50">
              💬 Active User Chat
            </div>
            <a 
              href="/admin/dev-console" 
              className="block px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 rounded-md transition"
            >
              ⚙️ Developer Panel
            </a>
          </nav>
        </div>
        <div className="text-xs text-slate-600 border-t border-slate-800 pt-4">
          Status: Verified Standalone
        </div>
      </div>

      {/* Primary Interaction Interface */}
      <div className="flex-1 flex flex-col h-full bg-gradient-to-b from-slate-900 to-slate-950">
        {/* Top Boundary Bar */}
        <div className="h-14 border-b border-slate-800 flex items-center px-6 justify-between bg-slate-900/50 backdrop-blur-sm">
          <div className="text-sm font-medium text-slate-400">Secure Client Workspace</div>
          <div className="text-xs px-2 py-1 bg-slate-800 border border-slate-700 rounded text-slate-400">
            Routing: Local DB + Live Web
          </div>
        </div>

        {/* Dynamic Chat Feed Window */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-4xl w-full mx-auto">
          {messages.map((msg, index) => (
            <div 
              key={index} 
              className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role !== "user" && (
                <div className="h-8 w-8 rounded bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-xs font-bold text-slate-950 shadow-md shrink-0">
                  AI
                </div>
              )}
              
              <div className={`max-w-2xl rounded-xl px-4 py-3 text-sm shadow-sm leading-relaxed border ${
                msg.role === "user" 
                  ? "bg-emerald-600 text-white border-emerald-500 shadow-emerald-900/10" 
                  : "bg-slate-800/80 text-slate-200 border-slate-700/60 backdrop-blur-sm"
              }`}>
                {msg.content === "" && isStreaming ? (
                  <div className="flex items-center gap-1.5 py-1">
                    <span className="h-1.5 w-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                    <span className="h-1.5 w-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                    <span className="h-1.5 w-1.5 bg-slate-400 rounded-full animate-bounce"></span>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
              </div>

              {msg.role === "user" && (
                <div className="h-8 w-8 rounded bg-slate-700 flex items-center justify-center text-xs font-medium text-slate-200 shrink-0 border border-slate-600">
                  ME
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Floating Input Controller */}
        <div className="p-4 bg-gradient-to-t from-slate-950 to-transparent">
          <form onSubmit={handleSubmit} className="max-w-3xl mx-auto relative group">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isStreaming ? "Agent is processing query tools..." : "Ask your local agent a question or search live web trends..."}
              disabled={isStreaming}
              className="w-full bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-xl pl-4 pr-16 py-3.5 text-sm text-slate-100 placeholder-slate-500 shadow-xl focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-600 text-slate-950 font-bold px-4 py-1.5 rounded-lg text-xs tracking-wide uppercase transition shadow-md"
            >
              Send
            </button>
          </form>
          <div className="text-center text-[10px] text-slate-600 mt-2">
            Multi-Agent Router Layer • Connected on Live Port Localhost
          </div>
        </div>
      </div>
    </div>
  );
}