'use client';
import { useState, useEffect } from 'react';

export default function AuthGate({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      setIsAuthenticated(true);
    }
    setLoading(false);
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    
    try {
      const res = await fetch('http://127.0.0.1:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });

      const data = await res.json();

      if (res.ok) {
        localStorage.setItem('auth_token', data.access_token);
        setIsAuthenticated(true);
      } else {
        setError(data.detail || 'Access Denied.');
      }
    } catch (err) {
      setError('Cannot connect to backend security server.');
    }
  };

  if (loading) return <div className="p-8 text-center text-slate-400">Loading security scope...</div>;

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
        <form onSubmit={handleLogin} className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
          <h2 className="text-xl font-bold text-slate-100 mb-2">TIB Platform Gate</h2>
          <p className="text-sm text-slate-400 mb-6">Enter administrative credentials to connect to core architecture.</p>
          
          <input
            type="password"
            placeholder="Enter security password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-slate-200 outline-none focus:border-blue-500 transition-colors"
          />
          
          {error && <p className="mt-3 text-xs text-red-400 font-medium">{error}</p>}
          
          <button type="submit" className="mt-6 w-full rounded-lg bg-blue-600 py-2.5 font-semibold text-white hover:bg-blue-500 transition-colors">
            Unlock Interface
          </button>
        </form>
      </div>
    );
  }

  return <>{children}</>;
}