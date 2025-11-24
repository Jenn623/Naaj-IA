/*pagina de explorador*/

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar';
import DestinationCard from '../components/DestinationCard';
import ReviewModal from '../components/ReviewModal';
import PlaceDetailsModal from '../components/PlacesDetailsModal'; // 🆕 Importamos el modal de detalles
import { getDestinations, searchPlaces, getPlaceDetails } from '../services/api';
import '../styles/ExploreScreen.css';

const LOGO_URL = "/naaj-IA-icon.svg"; 

// --- DATOS DE RESPALDO (Por si falla la API) ---
const MOCK_DATA = [
  {
    nombre: "Fuerte de San Miguel",
    rating: 4.8,
    direccion: "Av. Escénica, Campeche",
    imagen: "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Fuerte_de_San_Miguel%2C_Campeche.jpg/640px-Fuerte_de_San_Miguel%2C_Campeche.jpg"
  },
  {
    nombre: "Calle 59",
    rating: 4.9,
    direccion: "Centro Histórico",
    imagen: "https://upload.wikimedia.org/wikipedia/commons/thumb/6/61/Calle_59_Campeche.jpg/640px-Calle_59_Campeche.jpg"
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
    imagen: "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/Edzna_Five_Floors_Pyramid.jpg/640px-Edzna_Five_Floors_Pyramid.jpg"
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
  
  // --- ESTADOS DE INTERFAZ ---
  const [scrolled, setScrolled] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // --- ESTADOS DE DATOS ---
  const [popularPlaces, setPopularPlaces] = useState([]);
  const [suggestedPlaces, setSuggestedPlaces] = useState([]);
  
  // --- ESTADOS DEL BUSCADOR ---
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  
  // --- ESTADOS DE LOS MODALES ---
  const [selectedPlace, setSelectedPlace] = useState(null); // Lugar activo
  const [showDetails, setShowDetails] = useState(false);    // Modal Ficha
  const [showReview, setShowReview] = useState(false);      // Modal Reseña

  // 1. CARGA INICIAL (GPS + API)
  useEffect(() => {
    const loadData = async () => {
      try {
        let data = { popular: [], suggested: [] };
        
        if ("geolocation" in navigator) {
          navigator.geolocation.getCurrentPosition(
            async (pos) => {
              data = await getDestinations(pos.coords.latitude, pos.coords.longitude);
              processData(data);
            },
            async () => {
              data = await getDestinations(); // Fallback sin GPS
              processData(data);
            }
          );
        } else {
          data = await getDestinations();
          processData(data);
        }
      } catch (error) {
        console.error("Error de conexión", error);
        useMockData();
        setLoading(false);
      }
    };

    const processData = (data) => {
      if (data && (data.popular.length > 0 || data.suggested.length > 0)) {
        setPopularPlaces(data.popular);
        setSuggestedPlaces(data.suggested);
      } else {
        useMockData();
      }
      setLoading(false);
    };

    const useMockData = () => {
      setPopularPlaces(MOCK_DATA);
      setSuggestedPlaces(MOCK_DATA.slice().reverse());
    };

    loadData();
  }, []);

  // 2. BUSCADOR (Debounce)
  useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (searchTerm.length > 2) {
        const results = await searchPlaces(searchTerm); 
        setSearchResults(results);
      } else {
        setSearchResults([]);
      }
    }, 500);

    return () => clearTimeout(delayDebounceFn);
  }, [searchTerm]);

  // 3. SCROLL HANDLER
  const handleScroll = (e) => {
    const scrollTop = e.target.scrollTop;
    setScrolled(scrollTop > 100);
  };

  // 4. ABRIR DETALLES DEL LUGAR (Lógica Unificada)
  const handleOpenPlace = async (placeName) => {
    // Limpiar buscador si estaba abierto
    setSearchTerm('');
    setSearchResults([]);

    // Obtener detalles completos del backend
    const fullDetails = await getPlaceDetails(placeName);
    
    if (fullDetails) {
      setSelectedPlace(fullDetails);
      setShowDetails(true); // Abre la ficha
    } else {
      // Fallback si la API falla en el detalle
      alert("Cargando información básica...");
      // Podrías pasar el objeto básico aquí si quisieras
    }
  };

  // 5. MANEJO DE RESEÑAS (Dentro de Detalles)
  const handleOpenReview = () => {
    setShowReview(true);
    // No cerramos Details, solo abrimos Review encima
  };

  const handleCloseReview = () => {
    setShowReview(false);
    // Opcional: Recargar detalles para ver la nueva reseña
    if (selectedPlace) handleOpenPlace(selectedPlace.nombre);
  };

  return (
    <div className="explore-screen">
      
      {/* HEADER FLOTANTE */}
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
            
            <div className={`greeting-container ${scrolled ? 'hidden' : ''}`}>
              <h1 className="title-naaj">¡Hola Explorador!</h1>
            </div>
          </div>

          {/* BUSCADOR */}
          <div className="search-wrapper">
            <div className="search-pill">
              <input 
                type="text"
                className="real-search-input"
                placeholder={scrolled ? 'Buscar...' : '¿Dónde te gustaría ir hoy?'}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              <div className="search-icon-circle">🔍</div>
            </div>

            {/* RESULTADOS DE BÚSQUEDA */}
            {searchResults.length > 0 && (
              <div className="search-results-dropdown">
                {searchResults.map((item, idx) => (
                  <div 
                    key={idx} 
                    className="search-result-item" 
                    onClick={() => handleOpenPlace(item.nombre)}
                  >
                    <div className="result-info">
                      <span className="result-name">{item.nombre}</span>
                      <span className="result-address">{item.direccion}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>

      {/* ZONA DE SCROLL (CUERPO) */}
      <div className="scroll-container" onScroll={handleScroll}>
        <div className="explore-body">
          
          {loading ? (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Cargando maravillas...</p>
            </div>
          ) : (
            <>
              {/* CARRUSEL 1: SUGERIDOS */}
              <div className="section-block">
                <div className="section-header">
                  <h3>Destinos Sugeridos</h3>
                  <span className="badge">Para ti</span>
                </div>
                <div className="horizontal-scroll">
                  {suggestedPlaces.map((place, idx) => (
                    <DestinationCard 
                      key={idx} 
                      place={place} 
                      onClick={() => handleOpenPlace(place.nombre)} 
                    />
                  ))}
                </div>
              </div>

              {/* CARRUSEL 2: POPULARES */}
              <div className="section-block popular-section">
                <div className="section-header">
                  <h3>Destinos Populares</h3>
                  <span className="badge-star">⭐ Top Rated</span>
                </div>
                <div className="horizontal-scroll">
                  {popularPlaces.map((place, idx) => (
                    <DestinationCard 
                      key={idx} 
                      place={place} 
                      onClick={() => handleOpenPlace(place.nombre)} 
                    />
                  ))}
                </div>
              </div>
            </>
          )}
          
          <div style={{ height: '100px' }}></div>
        </div>
      </div> 

      <NavBar />
      
      {/* MODALES APILADOS */}
      
      {/* 1. Ficha Técnica (Fondo) */}
      {showDetails && (
        <PlaceDetailsModal 
          place={selectedPlace} 
          onClose={() => setShowDetails(false)} 
          onAddReview={handleOpenReview} // Conecta con el siguiente modal
          isBlurred={showReview}         // Se desenfoca si el de reseña está abierto
        />
      )}

      {/* 2. Escribir Reseña (Frente) */}
      {showReview && (
        <ReviewModal 
          place={selectedPlace} 
          onClose={handleCloseReview} 
        />
      )}

    </div>
  );
};

export default ExploreScreen;