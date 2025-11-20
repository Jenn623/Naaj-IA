import google.generativeai as genai
import os
from dotenv import load_dotenv

# Carga tu clave API del archivo .env
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("Buscando modelos disponibles para 'generateContent'...\n")

# Itera sobre todos los modelos
for model in genai.list_models():
  # Revisa si el modelo soporta el método 'generateContent' (chat)
  if 'generateContent' in model.supported_generation_methods:
    print(f"- {model.name}")

print("\n¡Búsqueda completa!")