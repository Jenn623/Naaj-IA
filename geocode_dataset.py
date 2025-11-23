import os
import json
import requests
from dotenv import load_dotenv

# Carga tus claves del archivo .env
load_dotenv()
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

# AJUSTE: Rutas directas a tu archivo en la raíz
INPUT_PATH = "campeche.json"
OUTPUT_PATH = "campeche_actualizado.json"

def geocode_place(place_name, municipio="Campeche"):
    """Pregunta a Google dónde está este lugar exactamenete."""
    if not GOOGLE_KEY:
        print("❌ ERROR: No se encontró la GOOGLE_API_KEY en el archivo .env")
        return None
        
    query = f"{place_name}, {municipio}, Campeche, México"
    print(f"📡 Consultando a Google: {query}...")

    url = (
        "https://maps.googleapis.com/maps/api/place/textsearch/json?"
        f"query={query}&key={GOOGLE_KEY}"
    )

    try:
        response = requests.get(url).json()
        if response.get("results"):
            location = response["results"][0]["geometry"]["location"]
            return {"lat": location["lat"], "lng": location["lng"]}
    except Exception as e:
        print(f"Error de conexión: {e}")

    return None

def process_file():
    # 1. Abrimos tu archivo actual
    try:
        with open(INPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ No encuentro el archivo '{INPUT_PATH}'. Asegúrate de estar en la carpeta correcta.")
        return

    # 2. Recorremos los municipios buscando lugares sin coordenadas
    # Nota: Ajusta esta lógica según la estructura exacta de tu JSON. 
    # Si tu JSON tiene "restaurantes_famosos" directamente en la raíz:
    
    cambios = 0
    
    # A. Revisar "restaurantes_famosos"
    if "restaurantes_famosos" in data:
        for lugar in data["restaurantes_famosos"]:
            # Si no tiene coordenadas O las coordenadas son null/vacías
            if not lugar.get("coordenadas"):
                coords = geocode_place(lugar["nombre"])
                if coords:
                    lugar["coordenadas"] = coords
                    print(f"   ✅ Coordenada guardada para {lugar['nombre']}")
                    cambios += 1

    # B. Revisar "puntos_interes_recomendados" (Historia, Dulces, etc)
    if "puntos_interes_recomendados" in data:
        categorias = data["puntos_interes_recomendados"]
        for cat_nombre, lista_lugares in categorias.items():
            for lugar in lista_lugares:
                if not lugar.get("coordenadas"):
                    coords = geocode_place(lugar["nombre"])
                    if coords:
                        lugar["coordenadas"] = coords
                        print(f"   ✅ Coordenada guardada para {lugar['nombre']}")
                        cambios += 1

    # 3. Guardamos el archivo nuevo SOLO si hubo cambios
    if cambios > 0:
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✨ ¡Listo! Se actualizaron {cambios} lugares.")
        print(f"📁 Nuevo archivo creado: {OUTPUT_PATH}")
        print("👉 AHORA: Borra 'campeche.json' y renombra 'campeche_actualizado.json' a 'campeche.json'.")
    else:
        print("\n👍 Todo parece estar al día. No se encontraron lugares sin coordenadas.")

if __name__ == "__main__":
    process_file()