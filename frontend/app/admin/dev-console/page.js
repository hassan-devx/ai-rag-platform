'use client';

import { useState } from 'react';
import { secureFetch } from '@/utils/api';

export default function DevConsole() {
  const [textInput, setTextInput] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [status, setStatus] = useState({ type: '', message: '' });
  const [loading, setLoading] = useState(false);

  // Handle file selection change
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setStatus({ type: '', message: '' });
    }
  };

  // Submit Text Core Function
  const handleTextSubmit = async (e) => {
    e.preventDefault();
    if (!textInput.trim() || loading) return;

    setLoading(true);
    setStatus({ type: 'info', message: 'Ingesting raw text stream into ChromaDB vector cache...' });

    try {
      const response = await secureFetch('http://127.0.0.1:8000/api/admin/ingest-file', {
        method: 'POST',
        body: JSON.stringify({ text: textInput }),
      });

      if (!response.ok) throw new Error('Text ingestion pipeline rejected packet.');

      setStatus({ type: 'success', message: '✓ Text content vectorized and successfully indexed.' });
      setTextInput('');
    } catch (err) {
      console.error(err);
      setStatus({ type: 'error', message: '🚨 Text ingestion structural failure.' });
    } finally {
      setLoading(false);
    }
  };


  // Submit File Core Function
  const handleFileSubmit = async (e) => {
    e.preventDefault();
    if (!selectedFile || loading) return;

    setLoading(true);
    setStatus({ type: 'info', message: `Parsing and processing document: "${selectedFile.name}"...` });

    // Pack file into FormData standard payload
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // NOTE: secureFetch naturally processes FormData and passes your JWT headers perfectly
      const response = await fetch('http://127.0.0.1:8000/api/admin/ingest-file', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: formData,
      });

      if (!response.ok) throw new Error('File validation parsing route crashed.');

      setStatus({ type: 'success', message: `✓ "${selectedFile.name}" successfully parsed, chunked, and cached inside ChromaDB!` });
      setSelectedFile(null);
      // Reset input element visually
      document.getElementById('file-input').value = '';
    } catch (err) {
      console.error(err);
      setStatus({ type: 'error', message: `🚨 File parser execution failed processing structural layers.` });
    } finally {
      setLoading(false);
    }
  };


  // Wipe Vector Cache Database Function
  const handleResetIndex = async () => {
    if (!confirm("⚠️ WARNING: Are you completely sure you want to flush the vector index? Your agent will lose all uploaded text memory records.")) return;

    setLoading(true);
    setStatus({ type: 'info', message: 'Flushing persistent ChromaDB vector cache blocks...' });

    try {
      const response = await secureFetch('http://127.0.0.1:8000/api/admin/reset-index', {
        method: 'POST'
      });

      if (!response.ok) throw new Error('Database reset handler execution failure.');

      setStatus({ type: 'success', message: '✓ System Index flushed successfully. Permanent storage is back to a pristine baseline.' });
    } catch (err) {
      console.error(err);
      setStatus({ type: 'error', message: '🚨 Vector index clearing operation rejected.' });
    } finally {
      setLoading(false);
    }
  };



  return (
    <div className="flex h-screen w-screen bg-slate-950 font-sans text-slate-100 overflow-hidden">
      
      {/* GLOBAL APPLICATION NAVIGATION SIDEBAR */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between p-4 shrink-0">
        <div className="space-y-6">
          <div>
            <h1 className="text-sm font-bold text-blue-400 uppercase tracking-widest px-2">ImageBuilder OS</h1>
            <p className="text-[10px] text-slate-500 px-2">v1.0.0 Core Active</p>
          </div>
          <nav className="space-y-1">
            <a href="/" className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 transition-all">
              💬 AI Agent Chat Room
            </a>
            <a href="/admin/dev-console" className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg bg-slate-800 text-white transition-all">
              🛠️ Developer Console
            </a>
          </nav>
        </div>
      </aside>

      {/* PRIMARY WORKSPACE MONITOR */}
      <main className="flex-1 flex flex-col h-full bg-slate-950 overflow-y-auto p-8 max-w-4xl mx-auto">
        <header className="mb-8 border-b border-slate-900 pb-4">
          <h2 className="text-xl font-bold tracking-tight text-slate-100">Knowledge Ingestion Developer Console</h2>
          <p className="text-xs text-slate-400 mt-1">Populate your RAG persistent engine vector context dynamically.</p>
        </header>

        {/* FEEDBACK APP STATUS NOTIFICATION MESSAGES */}
        {status.message && (
          <div className={`mb-6 p-4 rounded-xl border text-xs font-semibold transition-all ${
            status.type === 'success' ? 'bg-emerald-950/20 border-emerald-900/50 text-emerald-400' :
            status.type === 'error' ? 'bg-red-950/20 border-red-900/50 text-red-400' :
            'bg-blue-950/20 border-blue-900/50 text-blue-400 animate-pulse'
          }`}>
            {status.message}
          </div>
        )}

        <div className="grid grid-cols-1 gap-8">
          
          {/* SECTION A: TARGET FILE PARSING UPLOAD CONTROLS */}
          <section className="bg-slate-900/40 border border-slate-900 rounded-2xl p-6">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">📂 Structured Document File Parser</h3>
            <form onSubmit={handleFileSubmit} className="space-y-4">
              <div className="border-2 border-dashed border-slate-800 hover:border-slate-700 bg-slate-900/20 rounded-xl p-8 flex flex-col items-center justify-center text-center transition-all relative">
                <input 
                  type="file" 
                  id="file-input"
                  onChange={handleFileChange}
                  accept=".txt,.md,.pdf"
                  className="absolute inset-0 opacity-0 cursor-pointer"
                  disabled={loading}
                />
                <span className="text-2xl mb-2">📥</span>
                <p className="text-sm font-medium text-slate-300">
                  {selectedFile ? `Selected: ${selectedFile.name}` : 'Click to browse or drop document targets here'}
                </p>
                <p className="text-[10px] text-slate-500 mt-1">Supports plain text parsing engines (.txt, .md)</p>
              </div>
              <button
                type="submit"
                disabled={loading || !selectedFile}
                className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:pointer-events-none text-white font-semibold text-xs py-3 rounded-xl transition-all active:scale-[0.99]"
              >
                Execute Document Context Vectorization
              </button>
            </form>
          </section>

          {/* SECTION B: RAW TEXT PARSING INGESTION */}
          <section className="bg-slate-900/40 border border-slate-900 rounded-2xl p-6">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">✍️ Raw Content Paste Stream</h3>
            <form onSubmit={handleTextSubmit} className="space-y-4">
              <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Paste unformatted data chunks, code blocks, or system logs to write direct vectors..."
                rows={5}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-sm text-slate-200 outline-none focus:border-slate-700 placeholder:text-slate-600 transition-colors resize-none"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !textInput.trim()}
                className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 disabled:opacity-40 font-semibold text-xs py-3 rounded-xl transition-all"
              >
                Ingest String Packet
              </button>
            </form>
          </section>



          {/* SECTION C: PERSISTENT INDEX DESTRUCTION UTILITY */}
          <section className="bg-red-950/10 border border-red-900/30 rounded-2xl p-6">
            <h3 className="text-sm font-bold text-red-400 uppercase tracking-wider mb-2">🚨 Danger Zone: Core Index Control</h3>
            <p className="text-xs text-slate-400 mb-4">
              Completely flush the local storage memory layers. This purges all vectorized chunks instantly.
            </p>
            <button
              onClick={handleResetIndex}
              disabled={loading}
              className="bg-red-950/40 hover:bg-red-900 text-red-200 border border-red-900/50 disabled:opacity-30 font-semibold text-xs px-5 py-3 rounded-xl transition-all active:scale-[0.99]"
            >
              Flush Persistent ChromaDB Collection
            </button>
          </section>

        </div>
      </main>
    </div>
  );
}