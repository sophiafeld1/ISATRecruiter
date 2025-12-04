"use client"

import { useState, useRef, useEffect } from 'react';
import Image from 'next/image';
import { ModeToggle } from '@/components/mode-toggle';

interface Message {
  role: 'user' | 'bot';
  content: string;
}

export default function Home() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!message.trim() || isLoading) return;

    const userMessage = message.trim();
    setMessage('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: userMessage }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to get response');
      }

      setMessages(prev => [...prev, { role: 'bot', content: data.answer }]);
    } catch (error: any) {
      setMessages(prev => [...prev, { 
        role: 'bot', 
        content: `Sorry, I encountered an error: ${error.message || 'Unknown error'}` 
      }]);
    } finally {
      setIsLoading(false);
    }
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

        {/* Chat messages area */}
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="welcome-message">
              <h1 className="main-title">ISAT Recruiter</h1>
              <p>Ask me anything about the ISAT program!</p>
            </div>
          ) : (
            <div className="messages-list">
              {messages.map((msg, index) => (
                <div key={index} className={`message ${msg.role}`}>
                  <div className="message-content">
                    {msg.content}
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
          )}
        </div>

        {/* Input bar at bottom */}
        <form 
          className="input-bar"
          onSubmit={handleSubmit}
        >
          <input
            type="text"
            placeholder="Ask about ISAT"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="message-input"
            disabled={isLoading}
          />
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
