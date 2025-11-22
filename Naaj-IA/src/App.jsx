import React from 'react';

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import ChatScreen from './pages/ChatScreen';
import Home from './pages/Home';
import './App.css'; // Estilos globales si los tienes

// Componente placeholder para la pantalla que haremos luego
const ExploreScreen = () => (
  <div style={{ color: 'white', textAlign: 'center', paddingTop: '50px' }}>
    <h1>Próximamente: Explorar</h1>
    <a href="/" style={{color: 'white'}}>Volver al Inicio</a>
  </div>
);

function App() {
  return (
    <Router>
      <div className="app-container">
        <Routes>
          {/* Ruta Principal (Inicio) */}
          <Route path="/" element={<Home />} />
          
          {/* Ruta del Chat */}
          <Route path="/naaj" element={<ChatScreen />} />
          
          {/* Ruta de Exploración (Futura) */}
          <Route path="/explore" element={<ExploreScreen />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
