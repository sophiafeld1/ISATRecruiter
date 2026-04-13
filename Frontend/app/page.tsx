"use client"

import { useState, useRef, useEffect } from 'react';
import Image from 'next/image';
import { ModeToggle } from '@/components/mode-toggle';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  role: 'user' | 'bot';
  content: string;
}

interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
}

export default function Home() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
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
                <div className="message-content">
                  {msg.role === 'bot' ? (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
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
