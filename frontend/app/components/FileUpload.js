'use client';
import { useState, useRef } from 'react';

export default function FileUpload() {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState({ type: '', message: '' });
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      uploadFile(files[0]);
    }
  };

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      uploadFile(files[0]);
    }
  };

  const uploadFile = async (file) => {
    setLoading(true);
    setUploadStatus({ type: '', message: '' });

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Point this to your FastAPI local or production URL
      const response = await fetch('http://127.0.0.1:8000/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        setUploadStatus({ type: 'success', message: data.message });
      } else {
        setUploadStatus({ type: 'error', message: data.detail || 'Upload failed.' });
      }
    } catch (error) {
      setUploadStatus({ type: 'error', message: 'Could not connect to the ingestion server.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto p-4">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
          isDragging
            ? 'border-blue-500 bg-blue-50/10'
            : 'border-slate-700 hover:border-slate-500 bg-slate-900/50'
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
          accept=".py,.md,.markdown,.txt,.pdf,.json,.doc"
        />

        <div className="flex flex-col items-center justify-center space-y-3">
          {loading ? (
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
          ) : (
            <svg
              className="w-10 h-10 text-slate-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          )}
          
          <div className="text-slate-200 font-medium">
            {loading ? 'Processing through RAG Matrix...' : 'Drag & drop a file here, or click to browse'}
          </div>
          <p className="text-xs text-slate-500">
            Supports Python (.py), Markdown (.md), Textbooks/Manuals (.txt, .pdf)
          </p>
        </div>
      </div>

      {uploadStatus.message && (
        <div
          className={`mt-4 p-3 rounded-lg text-sm border ${
            uploadStatus.type === 'success'
              ? 'bg-emerald-950/30 text-emerald-400 border-emerald-800'
              : 'bg-rose-950/30 text-rose-400 border-rose-800'
          }`}
        >
          {uploadStatus.message}
        </div>
      )}
    </div>
  );
}