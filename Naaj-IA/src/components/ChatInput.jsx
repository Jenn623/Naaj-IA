// componente general que maneja el elemento de escritura y envío

import React, { useState, useRef, useEffect } from 'react';
import '../styles/ChatInput.css';

const ChatInput = ({ onSendMessage, isLoading }) => {
  const [text, setText] = useState('');
  const textareaRef = useRef(null); // Ahora sí funcionará

  // Función para auto-ajustar la altura
  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto'; // Reseteamos para calcular bien
      // Ajustamos a la altura del contenido, con tope de 80px
      textarea.style.height = `${Math.min(textarea.scrollHeight, 80)}px`;
    }
  };

  // Efecto para ajustar altura cuando cambia el texto
  useEffect(() => {
    adjustHeight();
  }, [text]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (text.trim() && !isLoading) {
      onSendMessage(text);
      setText('');
      // Forzamos el reset de altura a 1 línea al enviar
      if (textareaRef.current) textareaRef.current.style.height = 'auto'; 
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="input-container">
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          placeholder="Pregúntale algo a Naaj..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          rows={1}
        />
        <button type="submit" disabled={isLoading || !text.trim()}>
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
          </svg>
        </button>
      </form>
    </div>
  );
};

export default ChatInput;