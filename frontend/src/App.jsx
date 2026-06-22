import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Olá! A base de dados do Adobe Analytics já foi sincronizada. O que você gostaria de saber sobre as campanhas de hoje?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    const newHistory = [...messages, userMessage];
    setMessages(newHistory);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: userMessage.content,
          history: messages 
        }),
      });
      
      const data = await response.json();
      setMessages([...newHistory, { role: 'assistant', content: data.reply }]);
    } catch (error) {
      setMessages([...newHistory, { role: 'assistant', content: '⚠️ Erro de conexão com o Data Lake local.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <header className="chat-header">
        <h1>📊 Analytics AI Chatbot</h1>
        <div className="status-indicator">
          <span className="dot"></span> Base Sincronizada
        </div>
      </header>

      <div className="chat-box">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="bubble">
              {typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)}
            </div>
          </div>
        ))}
        {loading && <div className="message assistant"><div className="bubble">Consultando o Data Lake...</div></div>}
      </div>

      <form onSubmit={handleSendMessage} className="input-area">
        <input 
          type="text" 
          value={input} 
          onChange={(e) => setInput(e.target.value)} 
          placeholder="Ex: Qual campanha de R$ 9.99 teve mais acessos?"
          disabled={loading}
        />
        <button type="submit" disabled={loading}>Analisar</button>
      </form>
    </div>
  );
}

export default App;