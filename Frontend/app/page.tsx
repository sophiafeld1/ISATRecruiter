"use client"

import { useState, useRef, useEffect } from 'react';
import Image from 'next/image';
import { ModeToggle } from '@/components/mode-toggle';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { buildScheduleExportHtml } from '@/lib/buildScheduleExportHtml';
import {
  ArrowUp,
  CalendarRange,
  Download,
  GraduationCap,
  Info,
  Maximize2,
  Minimize2,
  PanelLeft,
  Sparkles,
  SquarePen,
  X,
} from 'lucide-react';

interface Message {
  role: 'user' | 'bot';
  content: string;
}

interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface PromptOptions {
  kind: 'single' | 'multi';
  options: string[];
}

const suggestedQuestions = [
  {
    label: 'Generate a course schedule',
    hint: 'Build a four-year plan',
    icon: CalendarRange,
  },
  {
    label: 'What is ISAT?',
    hint: 'How the program works',
    icon: GraduationCap,
  },
] as const;

function BrandLogo({ className }: { className?: string }) {
  return (
    <div className={className}>
      <Image
        src="/cise-logo.jpg"
        alt="JMU College of Integrated Science and Engineering"
        width={440}
        height={120}
        className="brand-logo"
        priority
      />
    </div>
  );
}

export default function Home() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [multiSelected, setMultiSelected] = useState<string[]>([]);
  const [singleSelected, setSingleSelected] = useState<string>('');
  const [fullscreenMessageIdx, setFullscreenMessageIdx] = useState<number | null>(null);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const scheduleMessageRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [message]);

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 900px)');
    const apply = () => setIsMobile(mq.matches);
    apply();
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  }, []);

  useEffect(() => {
    if (!isMobile) setMobileOpen(false);
  }, [isMobile]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      setAboutOpen(false);
      setMobileOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    const onFs = () => {
      if (!document.fullscreenElement) setFullscreenMessageIdx(null);
    };
    document.addEventListener("fullscreenchange", onFs);
    return () => document.removeEventListener("fullscreenchange", onFs);
  }, []);

  useEffect(() => {
    const lastBot = [...messages].reverse().find((m) => m.role === 'bot');
    const prompt = lastBot ? getPromptOptions(lastBot.content) : null;
    if (!prompt || prompt.kind !== 'multi') {
      setMultiSelected([]);
    }
    if (!prompt || prompt.kind !== 'single') {
      setSingleSelected('');
    }
  }, [messages]);

  const sendQuestion = async (questionText: string) => {
    const userMessage = questionText.trim();
    if (!userMessage || isLoading) return;
    setMobileOpen(false);
    setMessage('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          question: userMessage,
          conversation_history: conversationHistory
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to get response');
      }

      const answerText =
        typeof data.answer === 'string' && data.answer.trim()
          ? data.answer
          : 'Sorry, the server returned an empty answer. Check the API / Python logs.';
      setMessages(prev => [...prev, { role: 'bot', content: answerText }]);
      
      if (data.conversation_history && Array.isArray(data.conversation_history)) {
        setConversationHistory(data.conversation_history);
      }
    } catch (error: unknown) {
      const detail = error instanceof Error ? error.message : 'Unknown error';
      setMessages(prev => [...prev, { 
        role: 'bot', 
        content: `Sorry, I encountered an error: ${detail}` 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await sendQuestion(message);
  };

  const onComposerKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void sendQuestion(message);
    }
  };

  const startNewChat = () => {
    if (document.fullscreenElement) {
      void document.exitFullscreen().catch(() => {});
    }
    setFullscreenMessageIdx(null);
    setMessages([]);
    setConversationHistory([]);
    setMessage('');
    setMultiSelected([]);
    setSingleSelected('');
    setMobileOpen(false);
    inputRef.current?.focus();
  };

  const toggleSidebar = () => {
    if (window.matchMedia('(max-width: 900px)').matches) {
      setMobileOpen((open) => !open);
      return;
    }
    setDesktopCollapsed((collapsed) => !collapsed);
  };

  const isScheduleMessage = (content: string): boolean => {
    const low = content.toLowerCase();
    if (low.includes("<table") && (low.includes("### totals") || low.includes("<h3>"))) return true;
    const mdSchedule =
      low.includes("#### first year") &&
      low.includes("#### fourth year") &&
      low.includes("fall semester courses") &&
      low.includes("total planned credits");
    return mdSchedule;
  };

  const toggleFullscreen = async (index: number) => {
    const target = scheduleMessageRefs.current[index];
    if (!target) return;
    try {
      if (document.fullscreenElement === target) {
        await document.exitFullscreen();
        setFullscreenMessageIdx(null);
        return;
      }
      if (document.fullscreenElement) {
        await document.exitFullscreen();
        setFullscreenMessageIdx(null);
      }
      await target.requestFullscreen();
      setFullscreenMessageIdx(index);
    } catch {
      // no-op: browser may deny fullscreen in unsupported contexts
    }
  };

  const downloadSchedule = (index: number) => {
    const wrap = scheduleMessageRefs.current[index];
    if (!wrap) return;
    const inner = wrap.querySelector(".schedule-message-content");
    const htmlContent = inner ? inner.innerHTML : wrap.innerHTML;
    const html = buildScheduleExportHtml(htmlContent);
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "isat_schedule.html";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const getPromptOptions = (content: string): PromptOptions | null => {
    const text = content.toLowerCase();
    if (text.includes('what concentration do you want to complete')) {
      return {
        kind: 'single',
        options: ['Applied Biotechnology', 'Applied Computing', 'Energy', 'Environment and Sustainability', 'Industrial and Manufacturing Systems'],
      };
    }
    if (text.includes('which sector do you want to complete')) {
      return {
        kind: 'single',
        options: ['Applied Biotechnology', 'Applied Computing', 'Energy', 'Environment and Sustainability', 'Industrial and Manufacturing Systems'],
      };
    }
    if (text.includes('choose exactly 4 concentration courses from:')) {
      const match = content.match(/choose exactly 4 concentration courses from:\s*([^.]+)/i);
      if (!match) return null;
      const options = match[1].split(',').map((s) => s.trim()).filter(Boolean);
      return { kind: 'multi', options };
    }
    return null;
  };

  const toggleMultiOption = (opt: string) => {
    setMultiSelected((prev) => {
      if (prev.includes(opt)) return prev.filter((v) => v !== opt);
      if (prev.length >= 4) return prev;
      return [...prev, opt];
    });
  };

  const renderPromptOptions = (content: string) => {
    const prompt = getPromptOptions(content);
    if (!prompt) return null;
    if (prompt.kind === 'single') {
      return (
        <div className="prompt-options-panel">
          <div className="suggested-questions">
            {prompt.options.map((opt) => (
              <button
                key={opt}
                type="button"
                className={`suggestion-chip ${singleSelected === opt ? 'selected' : ''}`}
                onClick={() => {
                  setSingleSelected(opt);
                  void sendQuestion(opt);
                }}
                disabled={isLoading}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      );
    }
    return (
      <div className="prompt-options-panel">
        <p className="prompt-hint">Select exactly 4 courses</p>
        <div className="suggested-questions">
          {prompt.options.map((opt) => (
            <button
              key={opt}
              type="button"
              className={`suggestion-chip ${multiSelected.includes(opt) ? 'selected' : ''}`}
              onClick={() => toggleMultiOption(opt)}
              disabled={isLoading}
            >
              {opt}
            </button>
          ))}
          <button
            type="button"
            className="suggestion-chip submit-chip"
            onClick={() => {
              if (multiSelected.length === 4) {
                void sendQuestion(multiSelected.join(', '));
                setMultiSelected([]);
              }
            }}
            disabled={isLoading || multiSelected.length !== 4}
          >
            Submit {multiSelected.length}/4
          </button>
        </div>
      </div>
    );
  };

  const composer = (
    <form className="composer" onSubmit={handleSubmit}>
      <label className="sr-only" htmlFor="chat-input">Message ISAT Recruiter</label>
      <textarea
        id="chat-input"
        ref={inputRef}
        rows={1}
        placeholder="Ask about the ISAT program"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={onComposerKeyDown}
        className="message-input"
        disabled={isLoading}
      />
      <button
        type="submit"
        className="send-button"
        aria-label="Send message"
        disabled={isLoading || !message.trim()}
      >
        <ArrowUp size={18} strokeWidth={2.4} />
      </button>
    </form>
  );

  const disclaimer = (
    <p className="disclaimer">
      ISAT Recruiter can make mistakes. Confirm details on the{' '}
      <a href="https://www.jmu.edu/cise/isat/index.shtml" target="_blank" rel="noopener noreferrer">
        ISAT website
      </a>
      .
    </p>
  );

  const sidebarOpen = isMobile ? mobileOpen : !desktopCollapsed;

  return (
    <div className={`app-shell${desktopCollapsed ? ' collapsed' : ''}`}>
      {mobileOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close menu"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside className={`sidebar${mobileOpen ? ' mobile-open' : ''}`} aria-label="Sidebar">
        <div className="sidebar-tools">
          <button
            type="button"
            className="icon-button sidebar-collapse"
            aria-label="Hide sidebar"
            onClick={toggleSidebar}
          >
            <PanelLeft size={18} />
          </button>
          <button
            type="button"
            className="icon-button sidebar-close"
            aria-label="Close menu"
            onClick={() => setMobileOpen(false)}
          >
            <X size={18} />
          </button>
        </div>
        <BrandLogo className="brand-plate" />
        <div className="brand-name">ISAT Recruiter</div>
        <div className="brand-tag">JMU Integrated Science and Technology</div>
        <nav className="sidebar-nav">
          <button type="button" className="nav-button" onClick={startNewChat}>
            <SquarePen size={18} />
            <span>New chat</span>
          </button>
          <button
            type="button"
            className="nav-button"
            onClick={() => {
              setMobileOpen(false);
              setAboutOpen(true);
            }}
          >
            <Info size={18} />
            <span>About</span>
          </button>
        </nav>
        <div className="sidebar-footer">
          <ModeToggle labeled />
        </div>
      </aside>

      <main className="chat-main">
        <header className="topbar">
          <button
            type="button"
            className="icon-button topbar-toggle"
            aria-label={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
            aria-expanded={sidebarOpen}
            onClick={toggleSidebar}
          >
            <PanelLeft size={18} />
          </button>
          <div className="topbar-title">
            <span className="topbar-badge" aria-hidden>
              <Sparkles size={13} />
            </span>
            ISAT Recruiter
          </div>
          <button type="button" className="icon-button" aria-label="New chat" onClick={startNewChat}>
            <SquarePen size={18} />
          </button>
        </header>

        {messages.length === 0 ? (
          <div className="empty-stage">
            <div className="empty-inner">
              <BrandLogo className="hero-logo" />
              <div className="hero-mark" aria-hidden>
                <Sparkles size={24} />
              </div>
              <h1 className="hero-title">ISAT Recruiter</h1>
              <p className="hero-subtitle">Ask me anything about the ISAT program.</p>
              <div className="starter-grid">
                {suggestedQuestions.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.label}
                      type="button"
                      className="starter-card"
                      onClick={() => sendQuestion(item.label)}
                      disabled={isLoading}
                    >
                      <Icon size={18} className="starter-card-icon" />
                      <span className="starter-card-title">{item.label}</span>
                      <span className="starter-card-hint">{item.hint}</span>
                    </button>
                  );
                })}
              </div>
              {composer}
              {disclaimer}
            </div>
          </div>
        ) : (
          <>
            <div className="thread">
              <div className="thread-inner" aria-live="polite">
                {messages.map((msg, index) => {
                  const isSchedule = msg.role === 'bot' && isScheduleMessage(msg.content);
                  return (
                    <div key={index} className={`message ${msg.role}`}>
                      {msg.role === 'bot' && (
                        <div className="avatar" aria-hidden>
                          <Sparkles size={15} />
                        </div>
                      )}
                      <div
                        className={`message-stack${isSchedule ? ' schedule-message-wrap' : ''}`}
                        ref={(el) => {
                          if (isSchedule) scheduleMessageRefs.current[index] = el;
                        }}
                      >
                        {isSchedule && (
                          <div className="schedule-message-toolbar" aria-label="Schedule actions">
                            <button
                              type="button"
                              className="schedule-toolbar-btn"
                              title={fullscreenMessageIdx === index ? 'Exit fullscreen' : 'Expand schedule'}
                              aria-label={fullscreenMessageIdx === index ? 'Exit fullscreen' : 'Expand schedule'}
                              onClick={() => toggleFullscreen(index)}
                            >
                              {fullscreenMessageIdx === index ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                            </button>
                            <button
                              type="button"
                              className="schedule-toolbar-btn"
                              title="Download schedule as HTML"
                              aria-label="Download schedule"
                              onClick={() => downloadSchedule(index)}
                            >
                              <Download size={16} />
                            </button>
                          </div>
                        )}
                        <div className={`message-content${isSchedule ? ' schedule-message-content' : ''}`}>
                          {msg.role === 'bot' ? (
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              rehypePlugins={[rehypeRaw]}
                              components={{
                                a: ({ node: _node, ...props }) => (
                                  <a {...props} target="_blank" rel="noopener noreferrer" />
                                ),
                              }}
                            >
                              {msg.content}
                            </ReactMarkdown>
                          ) : (
                            msg.content
                          )}
                        </div>
                        {msg.role === 'bot' && index === messages.length - 1 && renderPromptOptions(msg.content)}
                      </div>
                    </div>
                  );
                })}
                {isLoading && (
                  <div className="message bot">
                    <div className="avatar" aria-hidden>
                      <Sparkles size={15} />
                    </div>
                    <div className="message-content loading" aria-label="ISAT Recruiter is thinking">
                      <span className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>
            <div className="composer-dock">
              <div className="composer-inner">
                {composer}
                {disclaimer}
              </div>
            </div>
          </>
        )}
      </main>

      {aboutOpen && (
        <div className="modal-backdrop" onClick={() => setAboutOpen(false)}>
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="about-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <h2 id="about-title">About</h2>
              <button
                type="button"
                className="icon-button"
                aria-label="Close about"
                onClick={() => setAboutOpen(false)}
              >
                <X size={18} />
              </button>
            </div>
            <p>
              ISAT Recruiter is a chatbot that answers questions about the ISAT program.
              To explore the ISAT website, use the link below.
            </p>
            <a
              className="modal-link"
              href="https://www.jmu.edu/cise/isat/index.shtml"
              target="_blank"
              rel="noopener noreferrer"
            >
              Visit the ISAT website
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
