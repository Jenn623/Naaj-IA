// componente general del navBar de la aplicación

import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import '../styles/NavBar.css';

const NavBar = () => {
  const navigate = useNavigate();
  const location = useLocation(); // Nos dice en qué ruta estamos actualmente

  // Función helper para saber si un botón debe estar "iluminado"
  const isActive = (path) => location.pathname === path;

  return (
    <div className="navbar">
      
      {/* BOTÓN 1: CASA -> Va a EXPLORAR */}
      <div 
        className={`nav-item ${isActive('/explore') ? 'active' : ''}`} 
        onClick={() => navigate('/explore')}
      >
        {/* Puedes usar un emoji o tu imagen SVG aquí */}
        <span role="img" aria-label="Inicio">🏠</span>
      </div>

      {/* BOTÓN 2: CHAT -> Va a NAAJ-IA */}
      <div 
        className={`nav-item ${isActive('/naaj') ? 'active' : ''}`} 
        onClick={() => navigate('/naaj')}
      >
        {/* Usamos un icono de chat o robot */}
        <span role="img" aria-label="Chat">💬</span>
      </div>

      {/* BOTÓN 3: PERFIL/CONFIG (Sin función por ahora) */}
      <div className="nav-item">
        <span role="img" aria-label="Configuración">⚙️</span>
      </div>

    </div>
  );
};

export default NavBar;