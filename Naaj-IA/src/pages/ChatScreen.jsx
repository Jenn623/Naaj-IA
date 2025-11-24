/* Página para la pantalla del chat, une todos los componentes */

import React, { useState, useRef, useEffect } from 'react';
import Header from '../components/Header';
import Message from '../components/Message';
import ChatInput from '../components/ChatInput';
import NavBar from '../components/NavBar';
import { sendMessageToNaaj } from '../services/api';
import '../styles/ChatScreen.css';

const ChatScreen = () => {
  // 1. Función auxiliar para obtener la fecha de HOY en México
  const getMexicoDate = () => {
    return new Date().toLocaleDateString('es-MX', { timeZone: 'America/Mexico_City' });
  };

  // Estado inicial (vacío al principio para permitir la carga)
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Nuevo estado para ubicación (para mantener la coherencia con lo que ya tenías)
  const [userLocation, setUserLocation] = useState({ lat: null, lng: null });

  const messagesEndRef = useRef(null);

  // ---------------------------------------------------------
  // 2. EFECTO DE CARGA INICIAL (Recuperar Memoria)
  // ---------------------------------------------------------
  useEffect(() => {
    // A. Obtener GPS (Igual que antes)
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude
          });
        },
        (error) => console.log("Ubicación no permitida")
      );
    }

    // B. RECUPERAR CHAT GUARDADO
    //const savedChat = localStorage.getItem('naaj_chat_session');
    const savedDate = localStorage.getItem('naaj_chat_date');
    const today = getMexicoDate();

    // Recuperar chat de la sesión actual
    const savedChat = sessionStorage.getItem('naaj_chat_session');
    
    if (savedChat) {
      setMessages(JSON.parse(savedChat));
    } else {
      // Si no hay sesión activa, iniciamos limpio
      setMessages([
        { id: 1, text: "¡Hola! Soy Naaj-IA. ¿En qué puedo ayudarte hoy?", isUser: false }
      ]);
    }
  }, []);

  // ---------------------------------------------------------
  // 3. EFECTO DE GUARDADO AUTOMÁTICO
  // ---------------------------------------------------------
  useEffect(() => {
    // Cada vez que 'messages' cambie, lo guardamos en el celular
    if (messages.length > 0) {
      sessionStorage.setItem('naaj_chat_session', JSON.stringify(messages));
    }
  }, [messages]);

  // Scroll automático
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // ---------------------------------------------------------
  // MANEJO DE MENSAJES (Igual que antes, solo pequeños ajustes)
  // ---------------------------------------------------------
  const handleSendMessage = async (text) => {
    const userMessage = { id: Date.now(), text: text, isUser: true, type: 'text' };
    // Actualizamos estado (esto disparará el useEffect de guardado arriba)
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const data = await sendMessageToNaaj(text, messages, userLocation);
      
      if (data.messages && data.messages.length > 0) {
        const newBotMessages = data.messages.map((msg, index) => ({
          id: Date.now() + 1 + index,
          text: msg.content,
          isUser: false,
          type: msg.type || 'text',
          altText: msg.alt_text // Corregido el typo anterior
        }));
        setMessages((prev) => [...prev, ...newBotMessages]);
      } else {
        const botMessage = { 
          id: Date.now() + 1, 
          text: data.answer || "Lo siento, no entendí.", 
          isUser: false, 
          type: 'text' 
        };
        setMessages((prev) => [...prev, botMessage]);
      }

    } catch (error) {
      console.error(error);
      const errorMessage = { 
        id: Date.now() + 1, 
        text: "Error de conexión. Intenta de nuevo.", 
        isUser: false, 
        type: 'text' 
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-screen">
      <Header />
      
      <div className="messages-container">
        {messages.map((msg) => (
          <Message 
            key={msg.id} 
            text={msg.text} 
            isUser={msg.isUser} 
            type={msg.type} 
            altText={msg.altText} 
          />
        ))}
        {loading && <div className="typing-indicator">Naaj está escribiendo...</div>}
        <div ref={messagesEndRef} />
      </div>

      {/* 🆕 AQUÍ ESTÁ LA CLAVE: Envolvemos ambos en chat-footer */}
    <div className="chat-footer">
       <ChatInput onSendMessage={handleSendMessage} isLoading={loading} />
       <NavBar />
    </div>
    </div>
  );
};

export default ChatScreen;