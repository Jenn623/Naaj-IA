import React from 'react';

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import ChatScreen from './pages/ChatScreen';
import Home from './pages/Home';
import ExploreScreen from './pages/ExploreScreen';
import './App.css'; // Estilos globales si los tienes


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
