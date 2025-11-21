// este archivo sirve para la centralización de las peticiones

import axios from 'axios';

// Creamos una instancia de axios con la URL base de tu backend
// Si tu backend corre en otro puerto o IP, cámbialo aquí.
const api = axios.create({
  baseURL: 'http://localhost:3000',
  headers: { 'Content-Type': 'application/json' }, 
});

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
