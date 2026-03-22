import { useState, useRef, useEffect } from 'react';
import { chatApi, type ChatMessage } from '../../lib/apiClient';

interface ChatPanelProps {
  engagementId: string;
  companyName: string;
}

const SUGGESTED_QUESTIONS = [
  'What are the most critical findings?',
  'Summarise the revenue data from financial sources.',
  'Are there any red flags I should flag to the partner?',
  'What did LinkedIn reveal about the leadership team?',
  'Compare the headcount data across sources.',
];

export function ChatPanel({ engagementId, companyName }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function send(question?: string) {
    const text = (question ?? input).trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const res = await chatApi.ask(engagementId, text);
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: res.answer, sources: res.sources },
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to get a response.';
      setError(msg);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="px-5 py-4 border-b border-theme-border shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-orange-500 text-lg">◈</span>
          <div>
            <h2 className="text-sm font-semibold text-theme-text">Ask KEEN</h2>
            <p className="text-xs text-theme-text-muted">
              Ask questions about the {companyName} pipeline
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 min-h-0">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-xs text-theme-text-muted font-mono uppercase tracking-wider">
              Suggested questions
            </p>
            {SUGGESTED_QUESTIONS.map(q => (
              <button
                key={q}
                onClick={() => send(q)}
                className="block w-full text-left text-sm px-4 py-3 rounded-lg border border-theme-border bg-theme-surface hover:border-orange-500/50 hover:bg-orange-500/5 text-theme-text-secondary transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div
              className={
                msg.role === 'user'
                  ? 'max-w-[80%] px-4 py-3 rounded-2xl rounded-tr-sm bg-orange-500 text-white text-sm'
                  : 'max-w-[90%] space-y-2'
              }
            >
              {msg.role === 'assistant' ? (
                <>
                  <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-theme-surface border border-theme-border text-sm text-theme-text whitespace-pre-wrap leading-relaxed">
                    {msg.content}
                  </div>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="flex flex-wrap gap-1 px-1">
                      {msg.sources.map(src => (
                        <span
                          key={src}
                          className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-orange-500/10 text-orange-400 border border-orange-500/20"
                        >
                          {src}
                        </span>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-theme-surface border border-theme-border">
              <div className="flex gap-1 items-center">
                <span className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="text-xs text-red-400 px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/20">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-5 py-4 border-t border-theme-border shrink-0">
        <div className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask anything about this pipeline…"
            rows={1}
            className="flex-1 resize-none bg-theme-surface border border-theme-border rounded-xl px-4 py-3 text-sm text-theme-text placeholder:text-theme-text-faint focus:outline-none focus:border-orange-500/50 transition-colors"
            style={{ maxHeight: '120px' }}
          />
          <button
            onClick={() => send()}
            disabled={!input.trim() || loading}
            className="shrink-0 w-10 h-10 rounded-xl bg-orange-500 hover:bg-orange-600 disabled:opacity-30 disabled:cursor-not-allowed text-white flex items-center justify-center transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 8L14 2L8 14L7 9L2 8Z" fill="currentColor" />
            </svg>
          </button>
        </div>
        <p className="text-[10px] text-theme-text-faint mt-2">
          Enter to send · Shift+Enter for new line · Answers cite the source system
        </p>
      </div>
    </div>
  );
}
