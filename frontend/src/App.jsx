import React, { useState } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Olá! Sou seu assistente de Adobe Analytics. Faça o upload do CSV diário e me pergunte sobre as campanhas.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [fileStatus, setFileStatus] = useState('Nenhum arquivo carregado');

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      setFileStatus('Carregando...');
      const response = await fetch('http://localhost:8000/upload-csv', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      setFileStatus(data.status === 'success' ? '✅ CSV Carregado!' : '❌ Erro no upload');
    } catch (error) {
      setFileStatus('❌ Falha na conexão com o servidor');
    }
  };

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
          history: messages // Passando o histórico para manter o contexto
        }),
      });
      
      const data = await response.json();
      setMessages([...newHistory, { role: 'assistant', content: data.reply }]);
    } catch (error) {
      setMessages([...newHistory, { role: 'assistant', content: '⚠️ Erro ao conectar com o servidor.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <header className="chat-header">
        <h1>📊 Analytics AI Copilot</h1>
        <div className="upload-section">
          <input type="file" accept=".csv" onChange={handleFileUpload} id="file-upload"/>
          <span className="file-status">{fileStatus}</span>
        </div>
      </header>

      <div className="chat-box">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="bubble">
              {msg.content}
            </div>
          </div>
        ))}
        {loading && <div className="message assistant"><div className="bubble">Pensando...</div></div>}
      </div>

      <form onSubmit={handleSendMessage} className="input-area">
        <input 
          type="text" 
          value={input} 
          onChange={(e) => setInput(e.target.value)} 
          placeholder="Ex: Qual foi a taxa de conversão da feature RENDAMAIS?"
        />
        <button type="submit" disabled={loading}>Enviar</button>
      </form>
    </div>
  );
}

export default App;