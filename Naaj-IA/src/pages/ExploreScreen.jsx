/*pagina de explorador*/

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar';
import DestinationCard from '../components/DestinationCard';
import ReviewModal from '../components/ReviewModal';
import PlaceDetailsModal from '../components/PlacesDetailsModal';
import { getDestinations, searchPlaces, getPlaceDetails } from '../services/api';
import '../styles/ExploreScreen.css';

const LOGO_URL = "/naaj-IA-icon.svg"; 

// DATOS DE RESPALDO (Solo se usan si tu Python está apagado o falla)
const MOCK_DATA = [
  { nombre: "Fuerte de San Miguel (Demo)", rating: 4.8, direccion: "Av. Escénica", imagen: "https://images.unsplash.com/photo-1585155967849-91c736533c65?w=600&q=80" },
  { nombre: "Calle 59 (Demo)", rating: 4.9, direccion: "Centro", imagen: "https://images.unsplash.com/photo-1518105779142-d975f22f1b0a?w=600&q=80" },
  { nombre: "Edzná (Demo)", rating: 5.0, direccion: "Valle de Edzná", imagen: "https://images.unsplash.com/photo-1590079081922-54216b429062?w=600&q=80" }
];

const ExploreScreen = () => {
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // Estados de datos
  const [popularPlaces, setPopularPlaces] = useState([]);
  const [suggestedPlaces, setSuggestedPlaces] = useState([]);
  
  // Estados de interacción
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedPlace, setSelectedPlace] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [showReview, setShowReview] = useState(false);

  // 1. CARGA DE DATOS (INTENTO REAL + FALLBACK)
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        // Intentamos conectar con tu Backend (app.py)
        // Esto leerá tu archivo campeche.json real
        const data = await getDestinations();
        
        if (data && (data.popular.length > 0 || data.suggested.length > 0)) {
          console.log("✅ Datos cargados del JSON/Backend");
          setPopularPlaces(data.popular);
          setSuggestedPlaces(data.suggested);
        } else {
          throw new Error("Lista vacía del backend");
        }
      } catch (error) {
        console.warn("⚠️ Backend no disponible, usando modo Demo:", error.message);
        // Si falla, usamos los datos falsos para que no se vea feo
        setPopularPlaces(MOCK_DATA);
        setSuggestedPlaces([...MOCK_DATA].reverse());
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  // 2. BUSCADOR
  useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (searchTerm.length > 2) {
        try {
            const results = await searchPlaces(searchTerm); 
            setSearchResults(results);
        } catch (e) { setSearchResults([]); }
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

  // 4. ABRIR DETALLES (Unificado)
  const handleOpenPlace = async (placeName) => {
    setSearchTerm('');
    setSearchResults([]);

    // Primero buscamos en los datos que ya tenemos cargados (para que sea instantáneo)
    const preloadedPlace = [...popularPlaces, ...suggestedPlaces].find(p => p.nombre === placeName);
    
    if (preloadedPlace) {
        setSelectedPlace(preloadedPlace);
        setShowDetails(true);
        // Opcional: Pedir datos extra frescos al backend en segundo plano
    } else {
        // Si vino del buscador y no lo tenemos en pantalla, pedimos detalles
        const fullDetails = await getPlaceDetails(placeName);
        if (fullDetails) {
            setSelectedPlace(fullDetails);
            setShowDetails(true);
        }
    }
  };

  const handleOpenReview = () => setShowReview(true);
  const handleCloseReview = () => setShowReview(false);

  return (
    <div className="explore-screen">
      
      <div className={`explore-header ${scrolled ? 'minimized' : ''}`}>
        <div className="header-content">
          <div className="header-branding">
            <div className="logo-container">
              <img src={LOGO_URL} alt="Naaj" onError={(e) => e.target.src = "https://placehold.co/100x100/white/e91e63?text=N"} />
            </div>
            <div className={`greeting-container ${scrolled ? 'hidden' : ''}`}>
              <h1 className="title-naaj">¡Hola Explorador!</h1>
            </div>
          </div>

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
            {searchResults.length > 0 && (
              <div className="search-results-dropdown">
                {searchResults.map((item, idx) => (
                  <div key={idx} className="search-result-item" onClick={() => handleOpenPlace(item.nombre)}>
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

      <div className="scroll-container" onScroll={handleScroll}>
        <div className="explore-body">
          {loading ? (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Cargando destinos...</p>
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
                    <DestinationCard key={idx} place={place} onClick={() => handleOpenPlace(place.nombre)} />
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
                    <DestinationCard key={idx} place={place} onClick={() => handleOpenPlace(place.nombre)} />
                  ))}
                </div>
              </div>
            </>
          )}
          <div style={{ height: '100px' }}></div>
        </div>
      </div> 

      <NavBar />
      
      {showDetails && (
        <PlaceDetailsModal 
          place={selectedPlace} 
          onClose={() => setShowDetails(false)} 
          onAddReview={handleOpenReview} 
          isBlurred={showReview}         
        />
      )}

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