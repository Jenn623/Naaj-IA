import React from 'react';
import '../styles/Message.css';

const Message = ({ text, isUser, type = 'text', altText }) => {
  
  // 1. Función para detectar enlaces (Links) - SE MANTIENE IGUAL
  const parseLinks = (text) => {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.split(urlRegex).map((part, index) => {
      if (part.match(urlRegex)) {
        let cleanUrl = part.replace(/[\]).,]+$/, ""); 
        
        // Si después de limpiar quedó algo (por si acaso)
        if (!cleanUrl) return part;
        return (
          <a 
            key={index} 
            href={cleanUrl} // Usamos la URL limpia
            target="_blank" 
            rel="noopener noreferrer" 
            className="message-link"
          >
            {/* Mantenemos el texto corto para que se vea bonito */}
            📍 Ver en Mapa
          </a>
        );
      }
      return part;
    });
  };

  // 2. Función MEJORADA: Formato de texto (Negritas y limpieza)
  const formatMessage = (text) => {
    if (!text) return "";

    // Esta Regex divide el texto buscando bloques de asteriscos (dobles o simples)
    // Captura cosas como **Texto** o *Texto* o ***Texto***
    const parts = text.split(/(\*+.*?\*+)/g);

    return parts.map((part, index) => {
      // Verificamos si la parte parece un texto formateado (empieza y termina con *)
      if (part.startsWith('*') && part.endsWith('*')) {
        
        // 🆕 LIMPIEZA AGRESIVA:
        // Esta línea borra TODOS los asteriscos al inicio y al final, sean 1, 2 o 3.
        const content = part.replace(/^[*]+|[*]+$/g, '');
        
        // Renderizamos en negrita (puedes cambiar strong por em si quisieras cursiva)
        return <strong key={index}>{content}</strong>;
      }
      
      // Si es texto normal, buscamos enlaces dentro
      return <span key={index}>{parseLinks(part)}</span>;
    });
  };

  const renderContent = () => {
    // CASO IMAGEN
    if (type === 'image') {
      if (text === "NO_IMAGE" || !text) return null;
      return (
        <div className="message-image-container">
          <img 
            src={text} 
            alt={altText || "Lugar turístico"} 
            className="message-img-content" 
            onError={(e) => {
              e.target.onerror = null; 
              e.target.src = "https://placehold.co/600x400?text=Error+Carga";
            }}
          />
        </div>
      );
    }

    // CASO TEXTO
    return <p>{formatMessage(text)}</p>;
  };

  return (
    <div className={`message-row ${isUser ? 'user-row' : 'naaj-row'}`}>
      <div className={`message-bubble ${isUser ? 'user-bubble' : 'naaj-bubble'}`}>
        {renderContent()}
      </div>
    </div>
  );
};

export default Message;