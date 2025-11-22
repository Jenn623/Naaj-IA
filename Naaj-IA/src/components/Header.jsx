// componente general del header

import React from 'react';
import '../styles/Header.css';

const Header = () => {
  return (
    <div className="header-container">
        {/* Puedes reemplazar el src con la ruta de tu imagen local o url */}
      <div className="avatar">
        <img src="./public/naaj-IA-icon.svg" alt="Naaj Avatar" />
      </div>
      <div className="header-info">
        <h2>Naaj-IA</h2>
        <span className="status">En línea</span>
      </div>
    </div>
  );
};

export default Header;