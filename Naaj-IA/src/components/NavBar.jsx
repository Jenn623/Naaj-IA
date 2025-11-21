// componente general del navBar de la aplicación

import React from 'react';
import '../styles/NavBar.css';

const NavBar = () => {
  return (
    <div className="navbar">
      <div className="nav-item active">
        <span>🏠</span> {/* Puedes usar iconos reales como FontAwesome */}
      </div>
      <div className="nav-item">
        <span>📍</span>
      </div>
      <div className="nav-item">
        <span>⚙️</span>
      </div>
    </div>
  );
};

export default NavBar;