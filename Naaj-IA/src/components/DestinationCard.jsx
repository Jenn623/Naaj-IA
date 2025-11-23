/*componente para las tarjetas con los destinos en la página de explorador*/

import React, { useState } from 'react';
import '../styles/DestinationCard.css';

const DestinationCard = ({ place, onClick }) => {
  const [imgError, setImgError] = useState(false);

  // --- BOLSA DE IMÁGENES DE RESERVA (GENÉRICAS DE CAMPECHE/TURISMO) ---
  // Usamos estas si la imagen real falla o es "NO_IMAGE"
  // --- IMÁGENES DE RESERVA (LINKS ESTABLES DE WIKIMEDIA) ---
  const fallbacks = [
    "https://images.unsplash.com/photo-1518105779142-d975f22f1b0a?w=500&q=80", // Calle colorida
    "https://images.unsplash.com/photo-1590079081922-54216b429062?w=500&q=80", // Pirámide Maya
    "https://images.unsplash.com/photo-1565608087341-345c6f15793b?w=500&q=80", // Tacos
    "https://images.unsplash.com/photo-1626623375644-d26bbb19df70?w=500&q=80", // Arquitectura Colonial
    "https://images.unsplash.com/photo-1512813195386-6cf811ad3542?w=500&q=80"  // Comida Mexicana
  ];

  // Elegir imagen "random" pero fija según el nombre del lugar
  const getFallbackImage = (name) => {
    if (!name) return fallbacks[0];
    const index = name.length % fallbacks.length;
    return fallbacks[index];
  };

  // LÓGICA DE SELECCIÓN
  let displayImage;
  
  // Si hubo error al cargar, o no tiene imagen, o es el placeholder de texto "NO_IMAGE"
  if (imgError || !place.imagen || place.imagen === "NO_IMAGE") {
    displayImage = getFallbackImage(place.nombre);
  } else {
    displayImage = place.imagen;
  }

  return (
    <div 
      className="dest-card" 
      onClick={() => onClick(place)}
      style={{ backgroundImage: `url(${displayImage})` }} // Fondo CSS para llenar todo
    >
      {/* Imagen invisible solo para detectar errores de carga */}
      <img 
          src={place.imagen} 
          alt="detector"
          style={{ display: 'none' }}
          onError={() => {
            console.log("Falló imagen:", place.imagen); // Para ver en consola cuál falla
            setImgError(true);
          }}
        />

      <div className="dest-overlay">
        <h3 className="dest-name">{place.nombre}</h3>
        <div className="dest-info">
          <span className="dest-rating">⭐ {place.rating || "N.A."}</span>
          <span className="dest-btn-review">✍️ Opinar</span>
        </div>
      </div>
    </div>
  );
};

export default DestinationCard;