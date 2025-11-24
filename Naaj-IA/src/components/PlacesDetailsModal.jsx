import React from 'react';
import '../styles/PlaceDetailsModal.css';

const PlaceDetailsModal = ({ place, onClose, onAddReview, isBlurred }) => {
  if (!place) return null;

  // Fallback de imagen si viene vacía o NO_IMAGE
  const bgImage = (place.imagen && place.imagen !== "NO_IMAGE") 
    ? place.imagen 
    : "https://images.unsplash.com/photo-1596130152098-93e71bf4b274?w=600&q=80";

  // Formatear estado de apertura
  const getStatusText = (isOpen) => {
    if (isOpen === true) return <span className="status open">Abierto ahora 🟢</span>;
    if (isOpen === false) return <span className="status closed">Cerrado 🔴</span>;
    return <span className="status unknown">Horario no disponible ⚪</span>;
  };

  return (
    // Agregamos la clase 'blurred-mode' si el modal de reseña está abierto encima
    <div className={`details-overlay ${isBlurred ? 'blurred-mode' : ''}`} onClick={!isBlurred ? onClose : undefined}>
      
      <div className="details-card" onClick={(e) => e.stopPropagation()}>
        
        {/* HEADER */}
        <div className="details-header" style={{ backgroundImage: `url(${bgImage})` }}>
          {/* Ocultamos el botón de cerrar si está borroso para que no se distraiga */}
          {!isBlurred && (
            <button className="close-details-btn" onClick={onClose}>&times;</button>
          )}
          <div className="header-gradient">
            <h2>{place.nombre}</h2>
            <p className="details-rating">
              ⭐ {place.rating} <small>({place.rating_source || "Google"})</small>
            </p>
          </div>
        </div>

        {/* BODY */}
        <div className="details-body">
          
          <div className="info-section">
            <div className="info-row">
              <div className="info-item">
                <span className="icon">📍</span>
                <p>{place.direccion}</p>
              </div>
              <div className="info-item">
                <span className="icon">🕒</span>
                <p>{getStatusText(place.abierto_ahora)}</p>
              </div>
            </div>

            {/* 🆕 BOTÓN DE AGREGAR RESEÑA (Debajo del horario) */}
            <button className="action-review-btn" onClick={onAddReview}>
               Escribe una reseña
            </button>
          </div>

          <hr className="divider" />

          {/* RESEÑAS */}
          <div className="reviews-section">
            <h3>Opiniones de la comunidad</h3>
            
            {place.reviews && place.reviews.length > 0 ? (
              <div className="reviews-list">
                {place.reviews.map((rev, idx) => (
                  <div key={idx} className="review-item">
                    <div className="review-header">
                      <span className="user-name">{rev.user || "Viajero"}</span>
                      <span className="review-stars">{"★".repeat(Math.round(rev.rating))}</span>
                    </div>
                    <p className="review-comment">"{rev.comment}"</p>
                    <small className="review-date">{rev.date}</small>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-reviews">
                <span className="empty-icon">💬</span>
                <p>Nadie ha comentado aún.</p>
                {/* Quitamos el botón de aquí porque ya está arriba más visible */}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
};

export default PlaceDetailsModal;