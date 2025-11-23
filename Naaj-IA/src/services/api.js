// este archivo sirve para la centralización de las peticiones

import axios from 'axios';

// Creamos una instancia de axios con la URL base de tu backend
// Si tu backend corre en otro puerto o IP, cámbialo aquí.
const api = axios.create({
  baseURL: 'https://naaj-ia-2.onrender.com',
  headers: { 'Content-Type': 'application/json' }, 
}); // baseURL: 'http://localhost:3000',
// baseURL: 'https://naaj-ia-1.onrender.com'

// Modificamos la firma para aceptar 'location'
export const sendMessageToNaaj = async (question, history = [], location = null) => {
  try {
    const cleanHistory = history.map(msg => ({
      text: msg.text,
      isUser: msg.isUser
    }));

    const response = await api.post('/naaj', {
      question: question,
      history: cleanHistory,
      
      // 🆕 ENVIAMOS LAT Y LNG (Si existen)
      lat: location ? location.lat : null,
      lng: location ? location.lng : null
    });
    
    return response.data;
  } catch (error) {
    console.error("Error:", error);
    throw error;
  }
};

// 🆕 OBTENER DESTINOS (Populares y Sugeridos)
export const getDestinations = async (lat = null, lng = null) => {
  try {
    // Si hay GPS, lo enviamos en la URL
    const query = lat && lng ? `?lat=${lat}&lng=${lng}` : '';
    const response = await api.get(`/naaj/destinations${query}`);
    return response.data;
  } catch (error) {
    console.error("Error obteniendo destinos:", error);
    return { popular: [], suggested: [] }; // Retorno seguro en caso de error
  }
};

// 🆕 ENVIAR RESEÑA
export const submitReview = async (reviewData) => {
  try {
    const response = await api.post('/review', reviewData);
    return response.data;
  } catch (error) {
    console.error("Error enviando reseña:", error);
    throw error;
  }
};

/*const isProduction = import.meta.env.MODE === 'production'; // Si usas Vite
// const isProduction = process.env.NODE_ENV === 'production'; // Si usas Create React App

const api = axios.create({
  baseURL: isProduction 
    ? 'https://nombre-de-tu-proyecto.onrender.com' // Usa esto si está en la nube
    : 'http://localhost:3000',                     // Usa esto si está en tu PC
  headers: { 'Content-Type': 'application/json' }, 
});*/
