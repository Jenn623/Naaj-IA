/* Página para la pantalla del chat, une todos los componentes */

import React, { useState, useRef, useEffect } from 'react';
import Header from '../components/Header';
import Message from '../components/Message';
import ChatInput from '../components/ChatInput';
import NavBar from '../components/NavBar';
import { sendMessageToNaaj } from '../services/api';
import '../styles/ChatScreen.css';

const ChatScreen = () => {
  // Estado inicial con un mensaje de bienvenida
  const [messages, setMessages] = useState([
    { id: 1, text: "¡Hola! Soy Naaj-IA. ¿En qué puedo ayudarte hoy sobre Campeche?", isUser: false }
  ]);
  const [loading, setLoading] = useState(false);

  // NUEVO ESTADO PARA UBICACIÓN
  const [userLocation, setUserLocation] = useState({ lat: null, lng: null });

  // Referencia para el scroll automático al último mensaje
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 🆕 EFECTO PARA OBTENER GPS AL INICIAR
  useEffect(() => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude
          });
          console.log("📍 Ubicación obtenida:", position.coords);
        },
        (error) => {
          console.log("⚠️ No se pudo obtener ubicación:", error.message);
          // No pasa nada, el backend funcionará en modo "general"
        }
      );
    }
  }, []);

  const handleSendMessage = async (text) => {
    // 1. Agregamos el mensaje del usuario
    const userMessage = { id: Date.now(), text: text, isUser: true, type: 'text' };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      // 2. Llamamos al Backend
      const data = await sendMessageToNaaj(text, messages, userLocation);
      
      // 3. PROCESAMOS LA RESPUESTA (Aquí está el cambio principal)
      
      if (data.messages && data.messages.length > 0) {
        // CASO A: El backend nos envió múltiples burbujas (Afirmación, Foto, Mapa)
        
        const newBotMessages = data.messages.map((msg, index) => ({
          id: Date.now() + 1 + index, // IDs únicos
          text: msg.content,          // El contenido (texto o url de imagen)
          isUser: false,
          type: msg.type || 'text',    // 'text' o 'image'
          altText: msg.alt_text
        }));

        // Agregamos todos los mensajes de Naaj al chat
        setMessages((prev) => [...prev, ...newBotMessages]);

      } else {
        // CASO B: Respuesta normal de una sola burbuja (fallback)
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
          <Message key={msg.id} text={msg.text} isUser={msg.isUser} type={msg.type} altText={msg.altText} />
        ))}
        {loading && <div className="typing-indicator">Naaj está escribiendo...</div>}
        <div ref={messagesEndRef} />
      </div>

      <ChatInput onSendMessage={handleSendMessage} isLoading={loading} />
      <NavBar />
    </div>
  );
};

export default ChatScreen;