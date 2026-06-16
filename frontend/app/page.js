'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function Home() {
  // State management for Chat Hub
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hello Hassan! Ask me anything, or feed context into the Developer Console." }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [agentStatus, setAgentStatus] = useState(""); 

  // Dummy secureFetch definition wrapper for safety—keeps your custom security token interceptor intact
  const secureFetch = window.secureFetch || fetch;

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input;
    setInput("");
    setLoading(true);
    setAgentStatus("routing");

    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
  try {
      const response = await secureFetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          prompt: userMessage,              
          session_id: "hassan_dev_session" 
        }), 
      });

      if (!response.ok) {
        throw new Error("Failed to connect to the AI Agent stream backend pipeline.");
      }

      // 💡 THIS MUST HAPPEN IMMEDIATELY:
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let accumulatedResponse = "";

      // Initialize the empty chat bubble
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        
        if (value) {
          const chunk = decoder.decode(value, { stream: !done });
          
          // Clean out status tags safely
          const cleanChunk = chunk.replace(/X-STATUS:\w+/g, "");
          
          if (cleanChunk) {
            accumulatedResponse += cleanChunk;
            setMessages((prev) => {
              const updated = [...prev];
              if (updated.length > 0) {
                updated[updated.length - 1].content = accumulatedResponse;
              }
              return updated;
            });
          }
        }
      }

      // If the loop finished but absolutely nothing was captured, provide a visible fallback message
      if (!accumulatedResponse.trim()) {
        setMessages((prev) => {
          const updated = [...prev];
          if (updated.length > 0) {
            updated[updated.length - 1].content = "⚠️ Core engine executed successfully, but the pipeline returned an empty response stream.";
          }
          return updated;
        });
      }

      setAgentStatus("");

    } catch (error) {
      console.error("Streaming error caught:", error);
      setAgentStatus("error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-screen bg-slate-950 font-sans text-slate-100 overflow-hidden">
      
      {/* ======================================================== */}
      {/* LEFT SIDEBAR: INTERFACE PLATFORM OPTIONS                 */}
      {/* ======================================================== */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between p-4 shrink-0">
        <div className="space-y-6">
          <div>
            <h1 className="text-sm font-bold text-blue-400 uppercase tracking-widest px-2">
              ImageBuilder OS
            </h1>
            <p className="text-[10px] text-slate-500 px-2">v1.0.0 Core Active</p>
          </div>

          <nav className="space-y-1">
            <a href="/" className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg bg-slate-800 text-white transition-all">
              💬 AI Agent Chat Room
            </a>
            <a href="/admin/dev-console" className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 transition-all">
              🛠️ Developer Console
            </a>
          </nav>
        </div>

        {/* Dynamic Safe Logout Area at the bottom of sidebar */}
        <div className="pt-4 border-t border-slate-800">
          <button 
            onClick={() => {
              localStorage.removeItem('auth_token');
              window.location.reload();
            }} 
            className="w-full text-left text-xs font-semibold px-3 py-2.5 bg-red-950/30 text-red-400 border border-red-900/40 rounded-lg hover:bg-red-900 hover:text-white transition-all"
          >
            ❌ Revoke Token (Log Out)
          </button>
        </div>
      </aside>

      {/* ======================================================== */}
      {/* PRIMARY CHAT WINDOW CONTAINER                            */}
      {/* ======================================================== */}
      <main className="flex-1 flex flex-col h-full bg-slate-950 relative">
        
        {/* Workspace Subheading Navbar */}
        <header className="h-14 border-b border-slate-900 flex items-center justify-between px-8 bg-slate-950/50 backdrop-blur-md">
          <span className="text-xs font-semibold text-slate-400">Secure Orchestration Workspace</span>
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="Backend pipeline linked" />
        </header>

        {/* Live Scrollable Message Streams */}
        <section className="flex-1 overflow-y-auto space-y-6 p-8 scrollbar-thin max-w-4xl w-full mx-auto pb-32">
          {messages.map((msg, idx) => (
            <div 
              key={idx} 
              className={`flex flex-col max-w-[85%] rounded-2xl p-4 border transition-all ${
                msg.role === "user" 
                  ? "bg-blue-600/10 border-blue-500/20 ml-auto items-end rounded-tr-none" 
                  : "bg-slate-900/40 border-slate-900 mr-auto items-start rounded-tl-none"
              }`}
            >
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">
                {msg.role === "user" ? "User Context" : "Agent Core"}
              </span>

              {/* CHAT DISPLAY HUB */}
              {/* CHAT DISPLAY HUB */}
<div className="text-sm leading-relaxed text-slate-200 max-w-none w-full">
  {msg.role === "assistant" ? (
    // 💡 Wrapped in a div to hold the space-y layout instead of passing it to ReactMarkdown directly
    <div className="space-y-2">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Custom split logic for inline vs block code blocks
          code({ node, inline, className, children, ...props }) {
            const isInline = !className && !String(children).includes('\n');
            return isInline ? (
              <code className="bg-slate-950 text-rose-400 font-mono text-xs px-1.5 py-0.5 rounded border border-slate-800/60" {...props}>
                {children}
              </code>
            ) : (
              <pre className="bg-slate-950 text-amber-400 font-mono text-xs p-4 rounded-xl border border-slate-800/80 overflow-x-auto my-3 whitespace-pre">
                <code {...props}>{children}</code>
              </pre>
            );
          },
          // Custom layouts for lists
          ul: ({ children }) => <ul className="list-disc list-inside space-y-1.5 my-2 text-slate-300 pl-2">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside space-y-1.5 my-2 text-slate-300 pl-2">{children}</ol>,
          // Custom styles for title headers
          h1: ({ children }) => <h1 className="text-lg font-bold text-blue-400 mt-4 mb-1 border-b border-slate-800/50 pb-1">{children}</h1>,
          h2: ({ children }) => <h2 className="text-base font-bold text-slate-300 mt-3 mb-1">{children}</h2>,
          h3: ({ children }) => <h3 className="text-sm font-semibold text-slate-400 mt-2 mb-1">{children}</h3>,
          p: ({ children }) => <p className="leading-relaxed mb-1">{children}</p>
        }}
      >
        {msg.content}
      </ReactMarkdown>
    </div>
  ) : 
  
  (
    // Simple plain-text display for the User bubble
    <p className="whitespace-pre-wrap text-slate-200">{msg.content}</p>
  )}
</div>
                     

            </div>
          ))}
        </section>

        {/* BOTTOM FLOATING CONTROLS PANEL */}
        <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-slate-950 via-slate-950/90 to-transparent">
          <div className="max-w-4xl mx-auto w-full">
            
            {/* Real-time Processing Status Badges Indicator */}
            {agentStatus && (
              <div className="mb-3 animate-pulse flex items-center gap-2 max-w-fit px-3 py-1.5 rounded-lg border text-xs font-semibold bg-slate-900 border-slate-800 shadow-xl backdrop-blur-sm transition-all">
                {agentStatus === "routing" && <span className="text-amber-400">🧭 Analyzing query structural context...</span>}
                {agentStatus === "local_knowledge_search" && <span className="text-cyan-400">💾 Searching local persistent vector store (ChromaDB)...</span>}
                {agentStatus === "live_web_search" && <span className="text-emerald-400">🌐 Executing live web discovery engine (DuckDuckGo)...</span>}
                {agentStatus === "synthesizing" && <span className="text-purple-400">🧠 Context retrieved. Synthesizing insights...</span>}
                {agentStatus === "error" && <span className="text-red-400">🚨 Core Routing Execution Exception Intercepted</span>}
              </div>
            )}

            {/* Chat Input Bar Submission Line */}
            <form onSubmit={handleSendMessage} className="flex gap-3 bg-slate-900 border border-slate-800 p-2.5 rounded-xl shadow-2xl focus-within:border-slate-700 transition-colors">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Query project records or run dynamic routing loops..."
                className="flex-1 bg-transparent px-3 py-1.5 text-sm text-slate-200 outline-none placeholder:text-slate-500"
                disabled={loading}
              />
              <button 
                type="submit" 
                className="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs px-5 py-2.5 rounded-lg active:scale-[0.98] transition-all disabled:opacity-50"
                disabled={loading || !input.trim()}
              >
                Send
              </button>
            </form>
          </div>
        </div>

      </main>
    </div>
  );
}