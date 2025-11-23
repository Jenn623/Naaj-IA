import os
import json
import requests
from math import radians, sin, cos, sqrt, atan2
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS, cross_origin
from dotenv import load_dotenv
import google.generativeai as genai
from langdetect import detect, LangDetectException
import re
import urllib.parse # 🆕 Necesario para crear links seguros
import random # 🆕 Para sugeridos aleatorios
from datetime import datetime # 🆕 Para fecha de reseña

# -----------------------------
# CONFIGURACIÓN INICIAL
# -----------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app)

try:
    with open("campeche.json", "r", encoding="utf-8") as f:
        CAMPECHE_DATA = json.load(f)
except FileNotFoundError:
    CAMPECHE_DATA = {}

# -----------------------------
# UTILIDADES
# -----------------------------
def haversine(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 9999.0
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def extract_keywords(text_list):
    STOP_WORDS = {
        "el", "la", "los", "las", "un", "una", "de", "del", "en", "a", "al", 
        "y", "o", "pero", "si", "no", "es", "son", "estoy", "quiero", "quisiera",
        "recomiendame", "dime", "donde", "hay", "cerca", "lugares", "para", "ir",
        "hola", "naaj", "gracias", "por", "favor", "que", "tal", "esta", "tan"
    }
    keywords = set()
    for phrase in text_list:
        clean_phrase = re.sub(r'[^\w\s]', '', phrase.lower())
        words = clean_phrase.split()
        for w in words:
            if w not in STOP_WORDS and len(w) > 2:
                keywords.add(w)
    return list(keywords)

# -----------------------------
# 🆕 GENERADOR DE LINKS SEGUROS
# -----------------------------
def generate_google_maps_link(lat, lng, name, address):
    """Crea un link infalible de Google Maps"""
    if lat and lng:
        # Opción A: Link exacto por coordenadas (El más seguro)
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    else:
        # Opción B: Búsqueda por nombre (Fallback)
        query = f"{name} {address}"
        encoded_query = urllib.parse.quote(query)
        return f"https://www.google.com/maps/search/?api=1&query={encoded_query}"

# -----------------------------
# GOOGLE PLACES API
# -----------------------------
def search_google_places(query, lat=None, lng=None):
    if not GOOGLE_API_KEY: return []
    base_url = "https://maps.googleapis.com/maps/api/place"
    results = []

    try:
        # 🆕 LÓGICA INTELIGENTE DE BÚSQUEDA
        # Si hay coordenadas, usamos 'nearbysearch'.
        # Si NO hay (o las desactivamos a propósito), usamos 'textsearch'.
        if lat and lng:
            print(f"🌐 Google (Nearby): '{query}' cerca de {lat},{lng}")
            url = f"{base_url}/nearbysearch/json?keyword={query}&location={lat},{lng}&radius=5000&language=es&key={GOOGLE_API_KEY}"
        else:
            safe_query = f"{query} Campeche Mexico"
            print(f"🌐 Google (Text): '{safe_query}'")
            url = f"{base_url}/textsearch/json?query={safe_query}&language=es&key={GOOGLE_API_KEY}"

        response = requests.get(url)
        data = response.json()

        if "results" in data:
            for place in data["results"][:3]:
                # Extraer coordenadas seguras
                p_lat = place["geometry"]["location"]["lat"]
                p_lng = place["geometry"]["location"]["lng"]
                
                # 🆕 GENERAMOS EL LINK AQUÍ (BACKEND)
                # Así Gemini no tiene que inventarlo
                maps_link = generate_google_maps_link(p_lat, p_lng, place.get("name"), place.get("vicinity"))

                place_data = {
                    "nombre": place.get("name"),
                    "direccion": place.get("vicinity") or place.get("formatted_address"),
                    "rating": place.get("rating", "N/A"),
                    "abierto_ahora": place.get("opening_hours", {}).get("open_now", None),
                    "origen": "Google Places (En vivo) 🟢",
                    "imagen": "NO_IMAGE",
                    "maps_url": maps_link # <--- Guardamos el link listo
                }
                results.append(place_data)

    except Exception as e:
        print(f"❌ Error Google Places: {e}")

    return results

# -----------------------------
# RETRIEVER HÍBRIDO
# -----------------------------
def retrieve_hybrid_data(query, history=[], lat=None, lng=None):
    combined_results = []
    
    # Keywords
    raw_texts = [query]
    if history:
        last_user = next((m['text'] for m in reversed(history) if m.get('isUser')), None)
        if last_user: raw_texts.append(last_user)
    keywords = extract_keywords(raw_texts)
    search_term = " ".join(keywords)

    # 🆕 DETECCIÓN DE "BÚSQUEDA LEJANA" (MUNICIPIOS)
    # Si el usuario menciona uno de estos lugares, IGNORAMOS su GPS actual
    # para permitir que busque fuera de su zona.
    target_locations = [
        "champoton", "champotón", "carmen", "ciudad del carmen", 
        "escárcega", "escarcega", "calakmul", "calkiní", "calkini", 
        "hecelchakán", "hecelchakan", "hopelchén", "hopelchen", 
        "palizada", "isla aguada", "seybaplaya", "tenabo", "candelaria"
    ]
    
    # Revisamos si la query menciona algún municipio lejano
    query_lower = query.lower()
    is_remote_search = any(loc in query_lower for loc in target_locations)

    if is_remote_search:
        print(f"🚀 Búsqueda remota detectada. Ignorando GPS local para buscar en todo el estado.")
        lat = None
        lng = None

    # 1. Búsqueda JSON (Local)
    json_hits = []
    # ... (Lógica de búsqueda JSON igual que antes) ...
    # SOLO AÑADIMOS LA GENERACIÓN DE LINKS AL JSON TAMBIÉN
    for item in CAMPECHE_DATA.get("restaurantes_famosos", []) + \
                [l for cat in CAMPECHE_DATA.get("puntos_interes_recomendados", {}).values() for l in cat]:
        
        txt = f"{item['nombre']} {item.get('categoria','')} {item.get('municipio','')}".lower()
        if any(k in txt for k in keywords):
            # Generar link seguro si tiene coordenadas
            coords = item.get("coordenadas")
            if coords:
                item["maps_url"] = generate_google_maps_link(coords["lat"], coords["lng"], item["nombre"], "")
            else:
                item["maps_url"] = generate_google_maps_link(None, None, item["nombre"], item.get("direccion","Campeche"))
            
            item["origen"] = "Datos Locales Naaj 🟠"
            json_hits.append(item)

    # Filtrado de duplicados simple por nombre
    unique_hits = {v['nombre']:v for v in json_hits}.values()
    json_hits = list(unique_hits)

    # Ordenar
    if lat and lng:
        for item in json_hits:
            coords = item.get("coordenadas")
            if coords:
                item["dist_km"] = round(haversine(lat, lng, coords["lat"], coords["lng"]), 2)
            else:
                item["dist_km"] = 9999
        json_hits.sort(key=lambda x: x.get("dist_km", 9999))

    combined_results.extend(json_hits[:4])

    # 2. Búsqueda Google
    trigger_words = ["abierto", "cerca", "restaurante", "comida", "valoracion", "rating", "precio"]
    # Si es búsqueda remota, SIEMPRE usamos Google para complementar
    needs_google = len(json_hits) < 2 or any(w in query.lower() for w in trigger_words) or is_remote_search

    if needs_google and len(search_term) > 2:
        google_hits = search_google_places(search_term, lat, lng)
        for g_item in google_hits:
            # Evitar duplicados con el JSON
            if not any(j["nombre"] == g_item["nombre"] for j in json_hits):
                combined_results.append(g_item)
    
    return combined_results

# -----------------------------
# PROMPT (CON REGLA DE AGRUPACIÓN DE LISTAS)
# -----------------------------
def build_prompt(user_question, retrieved_data, detected_lang, has_coords, history):
    location_msg = "GPS Provided" if has_coords else "Unknown"
    
    history_text = ""
    for msg in history[-3:]:
        role = "User" if msg.get('isUser') else "Naaj"
        history_text += f"{role}: {msg.get('text','')}\n"

    return f"""
Role: Naaj-IA, expert tourism guide for Campeche.

Context:
- User Location: {location_msg}
- History:
{history_text}

Current Question: "{user_question}"

Data Found:
{json.dumps(retrieved_data, ensure_ascii=False, indent=2)}

--- INSTRUCTIONS ---
1. **Data Usage:**
   - Use Google Data (🟢) for ratings/open status.
   - Use Naaj Data (🟠) for cultural facts.

2. **LINK HANDLING:**
   - Use the exact "maps_url" from data.
   - Do NOT use brackets [] or parentheses () for links. Just the raw URL.
   
3. **IDENTITY & ORIGINS (CRITICAL):**
   - **If the user asks "Who are you?":** Answer that you are Naaj, a digital tourist guide (and mention you are an axolotl if you like).
   - **If the user asks "Who created you?", "Who made you?", or "Who developed you?":**
     You MUST reply with this exact idea (translated to the user's language):
     "Soy un proyecto desarrollado por un pequeño grupo de estudiantes apasionados que buscan innovar y facilitar el turismo en México mediante el uso de Inteligencia Artificial."

4. **RESPONSE STRUCTURE (CRITICAL):**
   - You must split the response into EXACTLY 3 PARTS using "|||".
   - Do NOT use "|||" more than twice.

   **FORMAT FOR MULTIPLE RECOMMENDATIONS (LISTS):**
   - **PART 1 (Description):** List the names, ratings, and details of ALL recommended places here (numbered 1., 2., etc.).
   - **PART 2 (Image):** Provide the image URL of the #1 option (or "NO_IMAGE").
   - **PART 3 (Locations):** List the Addresses and Maps Links for ALL options here. Use a new line for each place.
     Example:
     1. Address A [maps_url_A]
     2. Address B [maps_url_B]

5. **Language Rule:**
   - Match the user's language exactly.
"""

# -----------------------------
# ENDPOINTS (IGUAL QUE ANTES)
# -----------------------------
@app.route('/imagenes-naaj/<path:filename>')
@cross_origin()
def serve_image(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(base_dir, 'static', 'images')
    return send_from_directory(image_dir, filename)

@app.route("/naaj", methods=["POST"])
def naaj():
    try:
        data = request.get_json()
        question = data.get("question")
        lat = data.get("lat")
        lng = data.get("lng")
        history = data.get("history", [])

        if not question: return jsonify({"error": "No question"}), 400

        try: lang = detect(question)
        except: lang = "es"

        results = retrieve_hybrid_data(question, history, lat, lng)
        prompt = build_prompt(question, results, lang, (lat and lng), history)
        
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        
        # Parseo de respuesta (Igual)
        raw_text = response.text
        messages_to_send = []
        if "|||" in raw_text:
            parts = raw_text.split("|||")
            if len(parts) > 0: messages_to_send.append({"type": "text", "content": parts[0].strip()})
            if len(parts) > 1:
                img = parts[1].strip()
                if "http" in img: messages_to_send.append({"type": "image", "content": img, "alt_text": "Lugar"})
            if len(parts) > 2: messages_to_send.append({"type": "text", "content": parts[2].strip()})
        else:
            messages_to_send.append({"type": "text", "content": raw_text})

        return jsonify({
            "answer": raw_text,
            "messages": messages_to_send,
            "sources": [r.get("origen") for r in results]
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
    
    
# -----------------------------
# ENDPOINT: OBTENER DESTINOS (LÓGICA SIMPLE)
# -----------------------------
@app.route("/naaj/destinations", methods=["GET"])
@cross_origin()
def get_destinations():
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)

        all_places = []
        
        # 1. Recolectar TODOS los lugares del JSON
        # Restaurantes
        all_places.extend(CAMPECHE_DATA.get("restaurantes_famosos", []))
        
        # Puntos de interés (aplanar categorías)
        for cat_list in CAMPECHE_DATA.get("puntos_interes_recomendados", {}).values():
            all_places.extend(cat_list)
            
        # Lugares creados por la comunidad (si existen)
        all_places.extend(CAMPECHE_DATA.get("lugares_comunidad", []))

        # 2. Lógica de "POPULARES" (Rating)
        # Ordenamos por rating descendente. Si no tiene, asumimos 4.0
        popular = sorted(
            all_places, 
            key=lambda x: float(x.get("rating", 4.0)), 
            reverse=True
        )[:8] # Top 8

        # 3. Lógica de "SUGERIDOS" (Ubicación o Aleatorio)
        suggested = []
        
        if lat and lng:
            # Si hay GPS: Ordenar por cercanía
            # Calculamos distancia temporalmente
            for p in all_places:
                coords = p.get("coordenadas")
                if coords:
                    p["_temp_dist"] = haversine(lat, lng, coords["lat"], coords["lng"])
                else:
                    p["_temp_dist"] = 9999 # Muy lejos
            
            # Ordenar de menor a mayor distancia
            suggested = sorted(all_places, key=lambda x: x.get("_temp_dist", 9999))[:8]
        else:
            # Si NO hay GPS: Aleatorio (Shuffle) para variedad
            import random
            # Hacemos una copia para no afectar el orden original
            pool = all_places.copy()
            random.shuffle(pool)
            suggested = pool[:8]

        return jsonify({
            "popular": popular,
            "suggested": suggested
        })

    except Exception as e:
        print(f"❌ Error en destinations: {e}")
        return jsonify({"popular": [], "suggested": []}), 500
    
# -----------------------------
# ENDPOINT: SUBIR RESEÑA (CON AUTO-CREACIÓN)
# -----------------------------
@app.route("/review", methods=["POST"])
@cross_origin()
def add_review():
    try:
        data = request.get_json()
        
        # Datos de la reseña
        place_name = data.get("place_name")
        user_rating = float(data.get("rating"))
        comment = data.get("comment", "")
        
        # 🆕 DATOS EXTRA DEL LUGAR (Por si es nuevo)
        # El frontend debe enviarnos esto si viene de Google
        place_address = data.get("address", "Dirección desconocida")
        place_coords = data.get("coords", None) # {lat, lng}
        place_category = data.get("category", "Lugar Recomendado")

        if not place_name or not user_rating:
            return jsonify({"error": "Faltan datos clave"}), 400

        # 1. Buscar si el lugar YA existe en nuestro JSON
        target_place = None
        target_list_name = None # Para saber en qué lista guardarlo
        
        # Buscamos en restaurantes
        for place in CAMPECHE_DATA.get("restaurantes_famosos", []):
            if place["nombre"] == place_name:
                target_place = place
                target_list_name = "restaurantes_famosos"
                break
        
        # Si no, buscamos en puntos de interés
        if not target_place:
            for cat_name, lista in CAMPECHE_DATA.get("puntos_interes_recomendados", {}).items():
                for place in lista:
                    if place["nombre"] == place_name:
                        target_place = place
                        # Nota: es difícil saber la categoría exacta aquí, solo lo encontramos
                        break

        # 2. LOGICA DE ADOPCIÓN (Si no existe, lo creamos)
        if not target_place:
            print(f"🆕 Lugar nuevo detectado: {place_name}. Agregándolo a la BD...")
            
            new_place_entry = {
                "nombre": place_name,
                "categoria": place_category,
                "direccion": place_address,
                "coordenadas": place_coords,
                "rating": user_rating, # Empieza con el rating de este usuario
                "reviews": [],
                "origen": "Agregado por Comunidad 👥",
                "imagen": "NO_IMAGE" 
            }
            
            # Lo guardamos en una lista especial o en restaurantes por defecto
            if "lugares_comunidad" not in CAMPECHE_DATA:
                CAMPECHE_DATA["lugares_comunidad"] = []
            
            CAMPECHE_DATA["lugares_comunidad"].append(new_place_entry)
            target_place = new_place_entry

        # 3. Agregar la reseña
        new_review = {
            "user": "Viajero",
            "rating": user_rating,
            "comment": comment,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        
        if "reviews" not in target_place:
            target_place["reviews"] = []
            
        target_place["reviews"].append(new_review)

        # 4. Recalcular Promedio (Importante para actualizar el rating global)
        total_score = sum(r["rating"] for r in target_place["reviews"])
        new_average = round(total_score / len(target_place["reviews"]), 1)
        target_place["rating"] = new_average

        # 5. Guardar cambios en el archivo físico
        with open("campeche.json", "w", encoding="utf-8") as f:
            json.dump(CAMPECHE_DATA, f, ensure_ascii=False, indent=2)

        return jsonify({
            "message": "Reseña guardada exitosamente", 
            "new_rating": new_average,
            "is_new_place": (target_list_name is None)
        })

    except Exception as e:
        print(f"Error guardando reseña: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000)) # en local: app.run(debug=True, port=5000)
    # host='0.0.0.0' es obligatorio para que sea accesible desde fuera del contenedor
    app.run(host='0.0.0.0', port=port)
    
    #en produccion: # Render nos da un puerto en la variable de entorno PORT, si no existe usa 5000
    #port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' es obligatorio para que sea accesible desde fuera del contenedor
    #app.run(host='0.0.0.0', port=port)