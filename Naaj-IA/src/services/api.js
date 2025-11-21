// este archivo sirve para la centralización de las peticiones

import axios from 'axios';

// Creamos una instancia de axios con la URL base de tu backend
// Si tu backend corre en otro puerto o IP, cámbialo aquí.
const api = axios.create({
  baseURL: 'http://localhost:3000',
  headers: { 'Content-Type': 'application/json' }, 
}); // baseURL: 'http://localhost:3000',
// baseURL: 'https://naaj-ia.onrender.com'

// AGREGAMOS EL PARÁMETRO 'history' AQUÍ
export const sendMessageToNaaj = async (question, history = []) => {
  try {
    // Limpiamos el historial para enviar solo texto y rol (ahorrar datos)
    const cleanHistory = history.map(msg => ({
      text: msg.text,
      isUser: msg.isUser
    }));

    const response = await api.post('/naaj', {
      question: question,
      history: cleanHistory, // <--- ENVIAMOS EL HISTORIAL
      // lat: ... (si lo tienes)
      // lng: ...
    });
    return response.data;
  } catch (error) {
    console.error("Error:", error);
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
