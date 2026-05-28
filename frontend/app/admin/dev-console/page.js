"use client";
import { useState } from "react";

export default function Home() {
  // State management for Ingestion
  const [docId, setDocId] = useState("");
  const [docText, setDocText] = useState("");
  const [ingestStatus, setIngestStatus] = useState("");

  // State management for Chat
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  // Send raw text documents to the Python API
  const handleIngest = async (e) => {
    e.preventDefault();
    setIngestStatus("Processing...");
    try {
      const res = await fetch("http://127.0.0.1:8000/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: docId, text: docText }),
      });
      const data = await res.json();
      if (data.status === "success") {
        setIngestStatus(`Success! Chunks processed: ${data.chunks_processed}`);
        setDocId("");
        setDocText("");
      } else {
        setIngestStatus("Ingestion failed.");
      }
    } catch (err) {
      setIngestStatus("Error connecting to backend server.");
    }
  };

  // Submit queries to the streaming chat API endpoint
  const handleChat = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userMessage = { role: "user", text: query };
    setMessages((prev) => [...prev, userMessage]);
    setQuery("");
    setLoading(true);

    // Initialize an empty placeholder message for the incoming text stream
    const assistantMessageId = Date.now();
    setMessages((prev) => [...prev, { id: assistantMessageId, role: "assistant", text: "" }]);

    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: query }),
      });

      if (!response.body) throw new Error("No readable stream response body.");
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      // Read chunk streams from FastAPI as they arrive from OpenAI
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        const chunkText = decoder.decode(value, { stream: !done });
        
        // Append incoming text chunk to the exact assistant message placeholder
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId ? { ...msg, text: msg.text + chunkText } : msg
          )
        );
      }
    } catch (err) {
      console.error("Streaming error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex h-screen bg-gray-900 text-gray-100 font-sans">
      {/* LEFT SIDEBAR: Knowledge base document ingestion panel */}
      <section className="w-1/3 bg-gray-950 p-6 border-r border-gray-800 flex flex-col gap-4">
        <h2 className="text-xl font-bold text-emerald-400">Knowledge Ingestion Base</h2>
        <p className="text-xs text-gray-400">Add custom knowledge assets into your local vector database cluster.</p>
        
        <form onSubmit={handleIngest} className="flex flex-col gap-3 mt-4">
          <input
            type="text"
            placeholder="Document ID (e.g., policy_2026)"
            className="p-2.5 bg-gray-900 border border-gray-700 rounded text-sm focus:outline-none focus:border-emerald-500"
            value={docId}
            onChange={(e) => setDocId(e.target.value)}
            required
          />
          <textarea
            placeholder="Paste raw knowledge base text here..."
            rows={10}
            className="p-2.5 bg-gray-900 border border-gray-700 rounded text-sm focus:outline-none focus:border-emerald-500 resize-none"
            value={docText}
            onChange={(e) => setDocText(e.target.value)}
            required
          />
          <button type="submit" className="bg-emerald-600 hover:bg-emerald-500 font-semibold p-2.5 rounded text-sm transition">
            Ingest Document
          </button>
        </form>
        {ingestStatus && <p className="text-xs mt-2 text-emerald-300 bg-gray-900 p-2 border border-gray-800 rounded">{ingestStatus}</p>}
      </section>

      {/* RIGHT PANEL: Interactive conversational AI streaming console */}
      <section className="w-2/3 flex flex-col h-full bg-gray-900">
        <header className="p-4 bg-gray-950 border-b border-gray-800 flex justify-between items-center">
          <h1 className="text-lg font-bold text-gray-200">Grounded RAG Inference Console</h1>
          <span className="text-xs bg-emerald-500/10 text-emerald-400 px-2.5 py-1 border border-emerald-500/20 rounded-full font-mono">Status: Connected</span>
        </header>

        {/* Conversation Feed */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center text-gray-500 max-w-md mx-auto">
              <p className="text-sm">Knowledge base empty or idling. Feed documents into the ingestion bank on the left, then query details here.</p>
            </div>
          )}
          {messages.map((msg, index) => (
            <div key={index} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-xl p-3.5 rounded-xl text-sm leading-relaxed shadow-sm ${msg.role === "user" ? "bg-emerald-600 text-white rounded-br-none" : "bg-gray-800 text-gray-100 border border-gray-700 rounded-bl-none"}`}>
                {msg.text || (loading && msg.role === "assistant" && <span className="animate-pulse text-gray-400">...</span>)}
              </div>
            </div>
          ))}
        </div>

        {/* Message Input Controls */}
        <footer className="p-4 bg-gray-950 border-t border-gray-800">
          <form onSubmit={handleChat} className="flex gap-2">
            <input
              type="text"
              placeholder="Query your knowledge documents..."
              className="flex-1 p-3 bg-gray-900 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-emerald-500"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading}
            />
            <button type="submit" disabled={loading} className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-800 font-semibold px-6 rounded-lg text-sm transition">
              Send
            </button>
          </form>
        </footer>
      </section>
    </main>
  );
}