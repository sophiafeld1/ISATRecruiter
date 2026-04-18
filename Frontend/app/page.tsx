"use client"

import { useState, useRef, useEffect } from 'react';
import Image from 'next/image';
import { ModeToggle } from '@/components/mode-toggle';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

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

export default function Home() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [multiSelected, setMultiSelected] = useState<string[]>([]);
  const [singleSelected, setSingleSelected] = useState<string>('');
  const [fullscreenMessageIdx, setFullscreenMessageIdx] = useState<number | null>(null);
  const scheduleMessageRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const suggestedQuestions = [
    "Generate a course schedule",
    "What is ISAT?",
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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
      
      // Update conversation history with the response from the API
      if (data.conversation_history && Array.isArray(data.conversation_history)) {
        setConversationHistory(data.conversation_history);
      }
    } catch (error: any) {
      setMessages(prev => [...prev, { 
        role: 'bot', 
        content: `Sorry, I encountered an error: ${error.message || 'Unknown error'}` 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await sendQuestion(message);
  };

  const isScheduleMessage = (content: string): boolean => {
    const low = content.toLowerCase();
    // Legacy HTML schedule from older API output
    if (low.includes("<table") && (low.includes("### totals") || low.includes("<h3>"))) return true;
    // Markdown four-year plan (paired Fall/Spring tables + summary)
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
    const html = `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>ISAT Schedule</title>
    <style>
      body { font-family: Georgia, serif; margin: 24px; color: #222; }
      table { width: 100%; border-collapse: collapse; margin: 10px 0 18px; font-size: 14px; }
      th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left; vertical-align: top; }
      th { background: #f2edf6; }
      h3 { margin: 16px 0 8px; }
    </style>
  </head>
  <body>${htmlContent}</body>
</html>`;
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

  return (
    <div className="chat-container">
      <div className="chat-card">
        {/* JMU Logo */}
        <div className="logo-container">
          <Image
            src="/cise-logo.jpg"
            alt="JMU CISE Logo"
            width={200}
            height={80}
            className="jmu-logo"
          />
        </div>

        {/* About button with hover popup */}
        <div className="about-container">
          <div className="about-trigger">
            About
          </div>
          <div className="about-popup">
            <h2>About</h2>
            <p>ISAT Recruitment Tool
              is a chatbot that answers questions about the ISAT program
              To explore the ISAT Website, click the link below.
            </p>
            <a href="https://www.jmu.edu/cise/isat/index.shtml">ISAT Website</a>
          </div>
        </div>

        {/* Dark mode toggle */}
        <ModeToggle />

        <div className="welcome-message">
          <h1 className="main-title">ISAT Recruiter</h1>
          <p>Ask me anything about the ISAT program!</p>
        </div>
        {/* Chat messages area */}
        <div className="messages-container">
          <div className="messages-list">
            {messages.length === 0 && !isLoading && (
              <div className="empty-chat-hint">
                Start by asking a question about ISAT.
              </div>
            )}
            {messages.map((msg, index) => (
              <div key={index} className={`message ${msg.role}`}>
                <div
                  className={`message-stack ${
                    msg.role === 'bot' && isScheduleMessage(msg.content) ? 'schedule-message-wrap' : ''
                  }`}
                  ref={(el) => {
                    if (msg.role === 'bot' && isScheduleMessage(msg.content)) {
                      scheduleMessageRefs.current[index] = el;
                    }
                  }}
                >
                  {msg.role === 'bot' && isScheduleMessage(msg.content) && (
                    <div className="schedule-message-toolbar" aria-label="Schedule actions">
                      <button
                        type="button"
                        className="schedule-toolbar-btn"
                        title={fullscreenMessageIdx === index ? "Exit fullscreen" : "Expand schedule"}
                        aria-label={fullscreenMessageIdx === index ? "Exit fullscreen" : "Expand schedule"}
                        onClick={() => toggleFullscreen(index)}
                      >
                        {fullscreenMessageIdx === index ? (
                          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                            <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
                          </svg>
                        ) : (
                          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                            <polyline points="15 3 21 3 21 9" />
                            <polyline points="9 21 3 21 3 15" />
                            <line x1="21" y1="3" x2="14" y2="10" />
                            <line x1="3" y1="21" x2="10" y2="14" />
                          </svg>
                        )}
                      </button>
                      <button
                        type="button"
                        className="schedule-toolbar-btn"
                        title="Download schedule as HTML"
                        aria-label="Download schedule"
                        onClick={() => downloadSchedule(index)}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                          <polyline points="7 10 12 15 17 10" />
                          <line x1="12" y1="15" x2="12" y2="3" />
                        </svg>
                      </button>
                    </div>
                  )}
                  <div
                    className={`message-content ${msg.role === 'bot' && isScheduleMessage(msg.content) ? 'schedule-message-content' : ''}`}
                  >
                    {msg.role === 'bot' ? (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypeRaw]}
                        components={{
                          a: ({ node, ...props }) => (
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
                  {msg.role === 'bot' && index === messages.length - 1 && (() => {
                    const prompt = getPromptOptions(msg.content);
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
                            className={`suggestion-chip submit-chip ${multiSelected.length === 4 ? 'selected' : ''}`}
                            onClick={() => {
                              if (multiSelected.length === 4) {
                                void sendQuestion(multiSelected.join(', '));
                                setMultiSelected([]);
                              }
                            }}
                            disabled={isLoading || multiSelected.length !== 4}
                          >
                            Submit 4 Courses
                          </button>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="message bot">
                <div className="message-content loading">
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

        <div className="suggested-questions" aria-label="Suggested questions">
          {suggestedQuestions.map((q) => (
            <button
              key={q}
              type="button"
              className="suggestion-chip"
              onClick={() => sendQuestion(q)}
              disabled={isLoading}
            >
              {q}
            </button>
          ))}
        </div>

        {/* Input bar at bottom */}
        <form 
          className="input-bar"
          onSubmit={handleSubmit}
        >
          <label className="search-label">
            <input
              type="text"
              placeholder="Ask about ISAT"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="message-input"
              disabled={isLoading}
              required
            />
            <span className="slash-icon">/</span>
          </label>
          <button
            type="submit"
            className="send-button"
            aria-label="Send question"
            disabled={isLoading || !message.trim()}
          >
            ↑
          </button>
        </form>
      </div>
    </div>
  );
}
