// componente general que permite mostrar una vista previa de búsquedas de google

import React, { useState } from 'react';
import './ImagePreview.css';

const ImagePreview = ({ placeName }) => {
  // Estado para manejar si la imagen falla
  const [imgError, setImgError] = useState(false);

  // Limpiamos el nombre
  const safeName = placeName ? placeName.trim() : "Campeche";
  const encodedName = encodeURIComponent(safeName + " Campeche Mexico tourism");

  // TRUCO: Usamos Pollinations AI para generar/buscar una imagen representativa al vuelo
  // Es gratuito y no requiere API Key. 
  // Si prefieres unsplash, podrías usar: `https://source.unsplash.com/featured/?${encodedName}` (aunque a veces falla)
  const imageUrl = `https://image.pollinations.ai/prompt/${encodedName}?width=400&height=300&nologo=true`;

  // URL para ver en Google (al hacer clic)
  const googleSearchUrl = `https://www.google.com/search?q=${placeName}+Campeche&tbm=isch`;

  return (
    <div className="image-preview-container">
      <div className="browser-mockup-header">
        <span className="browser-dot red"></span>
        <span className="browser-dot yellow"></span>
        <span className="browser-dot green"></span>
        <span className="browser-title">{safeName}</span>
      </div>

      <div className="image-wrapper">
        {!imgError ? (
          <img 
            src={imageUrl} 
            alt={safeName} 
            className="real-image-content"
            onError={() => setImgError(true)} // Si falla, mostramos fallback
            loading="lazy"
          />
        ) : (
          // Fallback si la imagen no carga: Un cuadro con el nombre
          <div className="image-fallback">
            <span>📸</span>
            <p>Ver fotos de {safeName}</p>
          </div>
        )}
      </div>

      <a 
        href={googleSearchUrl} 
        target="_blank" 
        rel="noopener noreferrer"
        className="view-more-link"
      >
        Ver galería real en Google ↗
      </a>
    </div>
  );
};

export default ImagePreview;