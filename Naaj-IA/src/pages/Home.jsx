// Página para la pantalla de inicio de naaj

import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Home.css';

const Home = () => {
  const navigate = useNavigate();

  return (
    <div className="home-container">
      {/* Logo o Texto Superior Izquierdo */}
      <div className="home-header">
        <span>NAAJ-IA</span>
      </div>

      {/* Contenido Central */}
      <div className="home-content">
        <h1 className="main-title">
          DESCUBRE<br />
          LOS<br />
          SECRETOS<br />
          DE<br />
          MÉXICO
        </h1>

        <div className="button-group">
          {/* Botón 1: Explorar (Placeholder) */}
          <button 
            className="primary-btn" 
            onClick={() => navigate('/explore')}
          >
            Explorar Ahora
          </button>

          {/* Botón 2: Ir al Chat */}
          <button 
            className="secondary-btn" 
            onClick={() => navigate('/naaj')}
          >
            Naaj-IA
          </button>
        </div>
      </div>
    </div>
  );
};

export default Home;