'use client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState } from 'react';

export default function ChatBubble({ role, content }) {
  const isAssistant = role === 'assistant';

  return (
    <div className={`flex w-full my-3 ${isAssistant ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 leading-relaxed shadow-sm ${
          isAssistant
            ? 'bg-slate-900 border border-slate-800 text-slate-100'
            : 'bg-blue-600 text-white'
        }`}
      >
        {isAssistant ? (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Format standard headers beautifully
              h1: ({ children }) => <h1 className="text-xl font-bold border-b border-slate-800 pb-1 mt-3 mb-2 text-white">{children}</h1>,
              h2: ({ children }) => <h2 className="text-lg font-semibold mt-4 mb-2 text-slate-200">{children}</h2>,
              h3: ({ children }) => <h3 className="text-base font-semibold mt-3 mb-1 text-slate-300">{children}</h3>,
              
              // Spacing out paragraphs and lists
              p: ({ children }) => <p className="mb-2 last:mb-0 text-sm md:text-base text-slate-300">{children}</p>,
              ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-1 text-slate-300">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-1 text-slate-300">{children}</ol>,
              li: ({ children }) => <li className="text-sm">{children}</li>,
              
              // Handle block code execution displays beautifully
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                const codeString = String(children).replace(/\n$/, '');
                
                return !inline ? (
                  <CodeBlock language={match ? match[1] : 'text'} code={codeString} />
                ) : (
                  <code className="bg-slate-800 px-1.5 py-0.5 rounded text-rose-400 font-mono text-sm" {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {content}
          </ReactMarkdown>
        ) : (
          <p className="text-sm md:text-base">{content}</p>
        )}
      </div>
    </div>
  );
}

// Sub-component to manage dark-themed terminal copy layouts
function CodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-4 overflow-hidden rounded-lg border border-slate-800 bg-black font-mono text-xs md:text-sm shadow-md">
      <div className="flex items-center justify-between bg-slate-900 px-4 py-1.5 text-slate-400 border-b border-slate-950">
        <span className="lowercase text-[11px] tracking-wider text-slate-500">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center space-x-1 rounded px-2 py-0.5 text-[11px] text-slate-400 hover:bg-slate-800 hover:text-white transition"
        >
          {copied ? (
            <span className="text-emerald-400">Copied!</span>
          ) : (
            <span>Copy Code</span>
          )}
        </button>
      </div>
      <div className="overflow-x-auto p-4 text-slate-300 select-text leading-5">
        <pre><code>{code}</code></pre>
      </div>
    </div>
  );
}