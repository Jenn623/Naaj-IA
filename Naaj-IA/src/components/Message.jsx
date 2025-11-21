import React from 'react';
import '../styles/Message.css';

// Agregamos la prop 'type' (puede ser 'text' o 'image')
const Message = ({ text, isUser, type = 'text' }) => {
  
  // Función auxiliar para convertir URLs en enlaces clicables (sencillo)
  const renderContent = () => {
    if (type === 'image') {
      return (
        <img 
          src={text} 
          alt="Lugar recomendado" 
          className="message-img-content" 
          onError={(e) => e.target.style.display = 'none'} // Si falla, se oculta
        />
      );
    }

    // Si es texto y contiene un link (http...), intentamos renderizarlo (opcional pero útil para el mapa)
    // Para mantenerlo simple, por ahora renderizamos el texto tal cual.
    // Si quieres que el link sea azul y clicable, avísame y agregamos esa lógica extra.
    return <p>{text}</p>;
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