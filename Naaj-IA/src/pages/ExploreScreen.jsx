/*pagina de explorador*/

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar';
import DestinationCard from '../components/DestinationCard';
import ReviewModal from '../components/ReviewModal';
import { getDestinations } from '../services/api';
import '../styles/ExploreScreen.css';

const LOGO_URL = "/logo.svg"; 

// --- 1. DATOS DE RESPALDO (MOCK DATA) ---
// Estos se mostrarán si la API falla o los links no cargan.
// Usamos 'placehold.co' que genera imágenes al vuelo (nunca fallan).
const MOCK_DATA = [
  {
    nombre: "Fuerte de San Miguel",
    rating: 4.8,
    direccion: "Av. Escénica, Campeche",
    imagen: "https://images.unsplash.com/photo-1585155967849-91c736533c65?w=500&q=80"
  },
  {
    nombre: "Calle 59",
    rating: 4.9,
    direccion: "Centro Histórico",
    imagen: "https://images.unsplash.com/photo-1518105779142-d975f22f1b0a?w=500&q=80"
  },
  {
    nombre: "Malecón de Campeche",
    rating: 4.7,
    direccion: "Av. Pedro Sainz",
    imagen: "https://images.unsplash.com/photo-1612633826752-7a356f22eb40?w=500&q=80"
  },
  {
    nombre: "Edzná",
    rating: 5.0,
    direccion: "Valle de Edzná",
    imagen: "https://images.unsplash.com/photo-1590079081922-54216b429062?w=500&q=80"
  },
  {
    nombre: "La Pigua",
    rating: 4.6,
    direccion: "Av. Miguel Alemán",
    imagen: "https://images.unsplash.com/photo-1565608087341-345c6f15793b?w=500&q=80"
  }
];

const ExploreScreen = () => {
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(false);
  const [popularPlaces, setPopularPlaces] = useState([]);
  const [suggestedPlaces, setSuggestedPlaces] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [selectedPlace, setSelectedPlace] = useState(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        // Intentamos llamar a la API
        // NOTA: Si estás en local, asegúrate que api.js apunte a localhost:5000
        const data = await getDestinations(); 
        
        // VERIFICACIÓN DE SEGURIDAD:
        // Si la API devolvió listas vacías (o falló), usamos MOCK_DATA
        if (data.popular && data.popular.length > 0) {
            setPopularPlaces(data.popular);
            setSuggestedPlaces(data.suggested);
        } else {
            // FALLBACK: Usamos los datos falsos para que NO se vea vacío
            console.log("API vacía o fallida, usando datos de respaldo.");
            setPopularPlaces(MOCK_DATA);
            setSuggestedPlaces(MOCK_DATA.slice().reverse()); // Invertimos para variar
        }
      } catch (error) {
        console.error("Error de conexión, usando respaldo", error);
        setPopularPlaces(MOCK_DATA);
        setSuggestedPlaces(MOCK_DATA);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const handleScroll = (e) => {
    const scrollTop = e.target.scrollTop;
    setScrolled(scrollTop > 100);
  };

  const handleCardClick = (place) => {
    setSelectedPlace(place);
    setShowModal(true);
  };

  return (
    <div className="explore-screen">
      
      {/* 1. HEADER (Ahora vive AFUERA del scroll, flotando arriba) */}
      <div className={`explore-header ${scrolled ? 'minimized' : ''}`}>
        <div className="header-content">
          <div className="header-branding">
            <div className="logo-container">
              <img 
                src={LOGO_URL} 
                alt="Naaj Logo" 
                onError={(e) => e.target.src = "https://placehold.co/100x100/white/e91e63?text=N"} 
              />
            </div>
            
            {/* Ocultamos esto con CSS cuando esté minimizado, no con JS, para que sea más suave */}
            <div className={`greeting-container ${scrolled ? 'hidden' : ''}`}>
              <h1 className="title-naaj">¡Hola Explorador!</h1>
            </div>
          </div>

          <div className="search-pill" onClick={() => navigate('/naaj')}>
            <span className="search-placeholder">
              {scrolled ? '🔍 Buscar...' : '¿Dónde te gustaría ir hoy?'}
            </span>
            <div className="search-icon-circle">
               <span style={{fontSize: '1.2rem'}}>🔍</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. ZONA DE SCROLL (Pasa por DEBAJO del header) */}
      <div className="scroll-container" onScroll={handleScroll}>
        
        {/* CUERPO */}
        <div className="explore-body">
          
          {/* ... (El contenido de loading y carruseles sigue IGUAL) ... */}
          {loading ? (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Cargando maravillas...</p>
            </div>
          ) : (
            <>
              <div className="section-block">
                <div className="section-header">
                  <h3>Destinos Sugeridos</h3>
                  <span className="badge">Para ti</span>
                </div>
                <div className="horizontal-scroll">
                  {suggestedPlaces.map((place, idx) => (
                    <DestinationCard key={idx} place={place} onClick={handleCardClick} />
                  ))}
                </div>
              </div>

              <div className="section-block popular-section">
                <div className="section-header">
                  <h3>Destinos Populares</h3>
                  <span className="badge-star">⭐ Top Rated</span>
                </div>
                <div className="horizontal-scroll">
                  {popularPlaces.map((place, idx) => (
                    <DestinationCard key={idx} place={place} onClick={handleCardClick} />
                  ))}
                </div>
              </div>
            </>
          )}
          
          <div style={{ height: '100px' }}></div>
        </div>
      </div> 

      <NavBar />
      {showModal && <ReviewModal place={selectedPlace} onClose={() => setShowModal(false)} />}
    </div>
  );
}
  export default ExploreScreen;