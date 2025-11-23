/*componente para el modal para hacer las reviews, es un demo por ahora*/

import React, { useState } from 'react';
import { submitReview } from '../services/api';
import '../styles/ReviewModal.css';

const ReviewModal = ({ place, onClose }) => {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (rating === 0) return alert("Por favor selecciona una calificación");

    setIsSubmitting(true);
    try {
      // Preparamos los datos (incluyendo datos extra por si es un lugar nuevo de Google)
      const reviewPayload = {
        place_name: place.nombre,
        rating: rating,
        comment: comment,
        // Datos de adopción:
        address: place.direccion || "Ubicación desconocida",
        coords: place.coordenadas || null,
        category: place.types ? place.types[0] : "Lugar Turístico"
      };

      await submitReview(reviewPayload);
      setSuccess(true);
      setTimeout(() => {
        onClose(); // Cierra el modal automáticamente después de 1.5 seg
      }, 1500);
    } catch (error) {
      alert("Error al guardar la reseña. Intenta de nuevo.");
      setIsSubmitting(false);
    }
  };

  if (!place) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        
        {success ? (
          <div className="success-message">
            <h3>¡Gracias! 🎉</h3>
            <p>Tu reseña ayuda a otros exploradores.</p>
          </div>
        ) : (
          <>
            <div className="modal-header">
              <h3>Calificar Lugar</h3>
              <button className="close-btn" onClick={onClose}>&times;</button>
            </div>
            
            <div className="place-preview">
               <h4>{place.nombre}</h4>
               <p className="place-address">{place.direccion}</p>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="star-rating">
                {[1, 2, 3, 4, 5].map((star) => (
                  <span
                    key={star}
                    className={`star ${star <= rating ? 'filled' : ''}`}
                    onClick={() => setRating(star)}
                  >
                    ★
                  </span>
                ))}
              </div>
              
              <textarea
                placeholder="Escribe tu experiencia aquí (opcional)..."
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows="3"
              />

              <button type="submit" className="submit-btn" disabled={isSubmitting}>
                {isSubmitting ? 'Enviando...' : 'Publicar Reseña'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
};

export default ReviewModal;