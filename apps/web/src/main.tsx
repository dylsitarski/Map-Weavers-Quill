import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Editor } from './Editor';
import './style.css';

export function App() {
  const [status, setStatus] = useState('Connecting…');
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    fetch('/api/health', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok || (await response.json()).status !== 'ok')
          throw Error('Unavailable');
        setStatus('Local server connected');
      })
      .catch(() => {
        setStatus('Server unavailable. Start make dev and reload.');
      })
      .finally(() => clearTimeout(timer));
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, []);
  return (
    <main>
      <h1>Map-Weaver’s Quill</h1>
      <p role="status">{status}</p>
      <Editor />
    </main>
  );
}

const root = document.getElementById('root');
if (!root) throw new Error('Missing application root');
createRoot(root).render(<App />);
