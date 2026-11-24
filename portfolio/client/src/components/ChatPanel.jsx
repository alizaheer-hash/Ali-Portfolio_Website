import React, { useEffect, useRef, useState } from 'react';
import { API_URL } from '../theme.js';
import { suggestedQuestions } from '../data.js';

const SpeechRecognition =
  typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

export default function ChatPanel({ open, onClose }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: "Hi! I can answer questions about Ali's projects, skills and education. I only use what's in his CV and project notes.", sources: [] },
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const recRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, busy]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape' && open) onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  async function ask(text) {
    const question = text.trim();
    if (!question || busy) return;
    setInput('');
    setMessages((m) => [...m, { role: 'user', text: question }]);
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: question }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || 'The assistant is unavailable right now.');
      setMessages((m) => [...m, { role: 'assistant', text: data.answer, sources: data.sources || [] }]);
    } catch (err) {
      setMessages((m) => [...m, { role: 'assistant', text: err.message || 'Something went wrong. Please try again.', sources: [], error: true }]);
    } finally {
      setBusy(false);
    }
  }

  function toggleVoice() {
    if (!SpeechRecognition) return;
    if (listening) { recRef.current?.stop(); return; }
    const rec = new SpeechRecognition();
    rec.lang = navigator.language || 'en-US';
    rec.interimResults = false;
    rec.onresult = (e) => ask(e.results[0][0].transcript);
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recRef.current = rec;
    setListening(true);
    rec.start();
  }

  return (
    <aside className={`chat ${open ? 'chat--open' : ''}`} aria-label="Ask my AI assistant" aria-hidden={!open} inert={!open ? '' : undefined}>
      <div className="chat__head">
        <div>
          <strong>Ask about Ali</strong>
          <span className="chat__sub">Answers come from his CV and projects</span>
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close assistant">
          <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M5 5l14 14M19 5L5 19" /></svg>
        </button>
      </div>

      <div className="chat__log" role="log" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={`msg msg--${m.role} ${m.error ? 'msg--error' : ''}`}>
            <p>{m.text}</p>
            {m.sources?.length > 0 && (
              <ul className="msg__sources" aria-label="Sources">
                {m.sources.map((s) => (
                  <li key={s.id}>
                    <a href={s.anchor || '#projects'} onClick={onClose}>{s.title}</a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {busy && <div className="msg msg--assistant"><p className="typing" aria-label="Assistant is typing">● ● ●</p></div>}
        {messages.length === 1 && (
          <div className="chat__suggest">
            {suggestedQuestions.map((q) => (
              <button key={q} className="chip" onClick={() => ask(q)}>{q}</button>
            ))}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form className="chat__form" onSubmit={(e) => { e.preventDefault(); ask(input); }}>
        <label htmlFor="chat-input" className="sr-only">Your question</label>
        <input id="chat-input" ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question…" maxLength={500} autoComplete="off" />
        {SpeechRecognition && (
          <button type="button" className={`icon-btn ${listening ? 'icon-btn--on' : ''}`} onClick={toggleVoice}
            aria-label={listening ? 'Stop listening' : 'Speak your question'} aria-pressed={listening}>
            <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0014 0M12 18v3" /></svg>
          </button>
        )}
        <button className="btn btn--solid" type="submit" disabled={busy || !input.trim()}>Ask</button>
      </form>
    </aside>
  );
}
