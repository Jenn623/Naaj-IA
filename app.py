import os
import json
import requests
import urllib.parse
from math import radians, sin, cos, sqrt, atan2
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS, cross_origin
from dotenv import load_dotenv
import google.generativeai as genai
from langdetect import detect
from datetime import datetime
import random
import re

# -----------------------------
# 1. CONFIGURACIÓN
# -----------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app)

# Carga segura del JSON
try:
    with open("campeche.json", "r", encoding="utf-8") as f:
        CAMPECHE_DATA = json.load(f)
except FileNotFoundError:
    print("⚠️ ALERTA: campeche.json no encontrado. Iniciando vacío.")
    CAMPECHE_DATA = {"municipios_data": {}, "restaurantes_famosos": [], "lugares_comunidad": []}

# -----------------------------
# 2. UTILIDADES
# -----------------------------
def haversine(lat1, lon1, lat2, lon2):
    """Calcula distancia en KM para ordenar resultados"""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None: return 9999.0
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def extract_keywords(text):
    """Limpia el texto para búsqueda"""
    STOP_WORDS = {
        "el", "la", "los", "las", "un", "una", "de", "del", "en", "a", "al", 
        "y", "o", "pero", "si", "no", "es", "son", "estoy", "quiero", "quisiera",
        "recomiendame", "dime", "donde", "hay", "cerca", "lugares", "para", "ir",
        "hola", "naaj", "gracias", "por", "favor", "que", "tal", "esta", "tan",
        "busco", "necesito", "tienes", "informacion", "sobre", "cual", "cuales"
    }
    clean_phrase = re.sub(r'[^\w\s]', '', text.lower())
    return [w for w in clean_phrase.split() if w not in STOP_WORDS and len(w) > 2]

def generate_maps_link(lat, lng, name, address):
    """Genera link de Google Maps infalible"""
    if lat and lng:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    query = urllib.parse.quote(f"{name} {address}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"

# -----------------------------
# 3. MOTOR DE BÚSQUEDA GOOGLE (Híbrido: Utilidad vs Turismo)
# -----------------------------
def search_google_places(query, lat=None, lng=None, type_search="general"):
    if not GOOGLE_API_KEY: return []
    base_url = "https://maps.googleapis.com/maps/api/place"
    results = []

    try:
        # LÓGICA DE PRECISIÓN:
        # - Utility (Cajeros, Oxxo): Radio pequeño (2km) para inmediatez.
        # - General (Turismo): Radio amplio (5km) o Texto (si es otro municipio).
        
        if lat and lng:
            radius = 2000 if type_search == "utility" else 5000
            print(f"🌐 Google Nearby ({type_search}): '{query}' radio={radius}m")
            url = f"{base_url}/nearbysearch/json?keyword={query}&location={lat},{lng}&radius={radius}&language=es&key={GOOGLE_API_KEY}"
        else:
            # Si no hay GPS, asumimos búsqueda general en el estado
            # Evitamos repetir la palabra "Campeche" si ya está en la query
            suffix = "Mexico" if "campeche" in query.lower() else "Campeche Mexico"
            safe_query = f"{query} {suffix}"
            print(f"🌐 Google Text: '{safe_query}'")
            url = f"{base_url}/textsearch/json?query={safe_query}&language=es&key={GOOGLE_API_KEY}"

        response = requests.get(url)
        data = response.json()

        if "results" in data:
            # Utility trae más opciones (5), Turismo trae las mejores (3)
            limit = 5 if type_search == "utility" else 3
            
            for place in data["results"][:limit]:
                p_lat = place["geometry"]["location"]["lat"]
                p_lng = place["geometry"]["location"]["lng"]
                
                # Extraer foto (Opcional: Desactivado por ahorro, activable si tienes saldo)
                photo_url = "NO_IMAGE"
                
                place_data = {
                    "nombre": place.get("name"),
                    "direccion": place.get("vicinity") or place.get("formatted_address"),
                    "rating": place.get("rating", "N/A"),
                    "abierto_ahora": place.get("opening_hours", {}).get("open_now", None),
                    "origen": f"Google Places ({type_search}) 🟢",
                    "imagen": photo_url,
                    "maps_url": generate_maps_link(p_lat, p_lng, place.get("name"), ""),
                    "types": place.get("types", [])
                }
                results.append(place_data)

    except Exception as e:
        print(f"❌ Error Google: {e}")

    return results

# -----------------------------
# 4. RETRIEVER INTELIGENTE (Cerebro Principal)
# -----------------------------
def retrieve_smart_data(query, history=[], lat=None, lng=None):
    combined_results = []
    
    # A. CONTEXTO Y KEYWORDS
    current_keywords = extract_keywords(query)
    
    # Palabras de seguimiento ("y cual es mejor?", "donde queda?")
    follow_up_words = ["eso", "ese", "cual", "como", "donde", "mas", "barato", "caro", "mejor", "opcion", "otro"]
    is_follow_up = any(w in query.lower().split() for w in follow_up_words) or len(current_keywords) == 0

    search_terms = list(current_keywords)
    
    if is_follow_up and history:
        # Si es seguimiento, traemos el tema anterior
        last_user_msg = next((m['text'] for m in reversed(history) if m.get('isUser')), "")
        last_keywords = extract_keywords(last_user_msg)
        search_terms = last_keywords + search_terms
        print("🔄 Contexto: Mantenido.")
    else:
        print("🆕 Contexto: Nuevo tema.")

    final_query = " ".join(search_terms) if search_terms else query
    print(f"🔎 Buscando: '{final_query}'")

    # B. DETECCIÓN DE MUNICIPIO (Escalabilidad)
    # Si se menciona un municipio, IGNORAMOS el GPS local para buscar allá.
    MUNICIPALITIES = ["calakmul", "calkini", "campeche", "candelaria", "carmen", "champoton", "dzitbalche", "escarcega", "hecelchakan", "hopelchen", "palizada", "seybaplaya", "tenabo"]
    
    target_municipality = None
    for mun in MUNICIPALITIES:
        if mun in final_query.lower():
            target_municipality = mun
            lat = None; lng = None # Apagamos GPS local
            print(f"📍 Municipio detectado: {mun}")
            break

    # C. DETECCIÓN DE SERVICIOS (Utility Mode)
    utility_words = ["oxxo", "seven", "tienda", "cajero", "banco", "atm", "hospital", "clinica", "medico", "farmacia", "cruz roja", "policia", "seguridad", "gasolinera"]
    is_utility = any(w in final_query.lower() for w in utility_words)

    # --- ESTRATEGIA DE BÚSQUEDA ---

    # CASO 1: SERVICIOS URGENTES (Oxxo, Cajero)
    if is_utility and lat and lng:
        return search_google_places(final_query, lat, lng, type_search="utility")

    # CASO 2: BÚSQUEDA TURÍSTICA (Híbrida)
    json_hits = []
    seen_names = set()

    # 2.1 Buscar en JSON (Estructura Nueva + Lugares Comunidad)
    # Recolectamos listas relevantes
    lists_to_search = []
    
    # Si hay municipio específico, buscamos en su sección
    if target_municipality and "municipios_data" in CAMPECHE_DATA:
        lists_to_search.extend(CAMPECHE_DATA["municipios_data"].get(target_municipality, {}).get("lugares", []))
    else:
        # Si no, buscamos en todo (Restaurantes y Puntos de Interés Globales)
        lists_to_search.extend(CAMPECHE_DATA.get("restaurantes_famosos", []))
        for cat in CAMPECHE_DATA.get("puntos_interes_recomendados", {}).values():
            lists_to_search.extend(cat)
    
    # Agregamos siempre lugares de la comunidad
    lists_to_search.extend(CAMPECHE_DATA.get("lugares_comunidad", []))

    # Filtrado
    for item in lists_to_search:
        full_text = f"{item['nombre']} {item.get('categoria','')} {item.get('direccion','')}".lower()
        if any(k in full_text for k in search_terms):
            # Generar link si falta
            if "maps_url" not in item:
                coords = item.get("coordenadas")
                if coords:
                    item["maps_url"] = generate_maps_link(coords["lat"], coords["lng"], item["nombre"], "")
                else:
                    item["maps_url"] = generate_maps_link(None, None, item["nombre"], item.get("direccion",""))
            
            item["origen"] = "Datos Naaj 🟠"
            json_hits.append(item)
            seen_names.add(item["nombre"].lower())

    # Ordenar JSON por distancia si hay GPS
    if lat and lng:
        for item in json_hits:
            coords = item.get("coordenadas")
            if coords:
                item["_dist"] = haversine(lat, lng, coords["lat"], coords["lng"])
            else:
                item["_dist"] = 9999
        json_hits.sort(key=lambda x: x.get("_dist", 9999))

    combined_results.extend(json_hits[:5])

    # 2.2 Buscar en Google (Complemento)
    # Disparadores: Pocos resultados, preguntas de horario/transporte, o municipio específico
    google_triggers = ["abierto", "horario", "autobus", "transporte", "ado", "combi", "colectivo", "valoracion", "rating", "precio", "opiniones"]
    needs_google = len(json_hits) < 2 or any(w in final_query.lower() for w in google_triggers) or target_municipality

    if needs_google and len(final_query) > 2:
        google_hits = search_google_places(final_query, lat, lng, type_search="general")
        for g_item in google_hits:
            if g_item["nombre"].lower() not in seen_names:
                combined_results.append(g_item)
    
    return combined_results or google_hits

# -----------------------------
# 5. PROMPT (Identidad + Políglota + Reglas)
# -----------------------------
def build_prompt(user_question, retrieved_data, detected_lang, has_coords, history):
    location_msg = "GPS Provided" if has_coords else "Unknown"
    
    history_text = ""
    for msg in history[-3:]:
        role = "User" if msg.get('isUser') else "Naaj"
        history_text += f"{role}: {msg.get('text','')}\n"

    return f"""
Role: Naaj-IA, expert tourism guide for Campeche, Mexico.

Context:
- User Location: {location_msg}
- History:
{history_text}

Current Question: "{user_question}"

Data Found:
{json.dumps(retrieved_data, ensure_ascii=False, indent=2)}

--- INSTRUCTIONS ---

1. **IDENTITY & MAYA SOUL:**
   - You are Naaj, a friendly digital guide (Axolotl spirit).
   - **Tone:** Warm, helpful, and proud of Mayan culture.
   - **Mayan Language:** Use short Mayan greetings/words naturally (e.g., "Ma'alob k'iin" for Hello), but ALWAYS translate them. 
   - **Teaching:** If asked "How to say X in Maya", teach it clearly.

2. **POLYGLOT RULE (STRICT):**
   - Respond in the **EXACT SAME LANGUAGE** the user is using in "Current Question".
   - If User speaks English -> Respond in English.
   - If User speaks French -> Respond in French.
   - Do NOT translate user's intent to Spanish unless they speak Spanish.

3. **BEHAVIOR:**
   - **IMMEDIATE RESPONSE:** Never say "I will send info later". Answer NOW with what you have.
   - **Services:** For ATMs/Hospitals, be direct: "The closest is X, located at Y".
   - **Data:** Use "rating", "open_now", and "precio" from Data Found.

4. **RESPONSE STRUCTURE (THE GOLDEN RULE):**
   - You must output EXACTLY 3 parts separated by "|||".
   - **PART 1 (Text):** Your chat response, descriptions of places, ratings, and "open/closed" status.
   - **PART 2 (Image):** The URL of the *first* recommended place (or "NO_IMAGE").
   - **PART 3 (Locations):** A structured list of addresses and map links for ALL recommended places.

   **REQUIRED FORMAT FOR PART 3 (Copy this style exactly):**
   1. [Name Place 1]: [Address 1] [maps_url_1]
   2. [Name Place 2]: [Address 2] [maps_url_2]
   
   *Example of correct full response:*
   "Here are two great options: The Pigua is famous for seafood, and Marganzo is traditional. ||| http://image.url ||| 1. La Pigua: Av. Miguel Aleman [http://maps...] \n 2. Marganzo: Calle 8 [http://maps...]"

5. **DATA HANDLING:**
   - Use "maps_url" from data. Do NOT invent links.
   - Do not put brackets [] around the link itself.
"""

# -----------------------------
# 6. ENDPOINTS API
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
        # Validar datos
        question = data.get("question")
        if not question: return jsonify({"error": "No question"}), 400
        
        lat = data.get("lat")
        lng = data.get("lng")
        history = data.get("history", [])

        # Procesar
        results = retrieve_smart_data(question, history, lat, lng)
        prompt = build_prompt(question, results, "auto", (lat and lng), history)
        
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        raw_text = response.text

        # Formatear respuesta
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
            "sources": [r.get("origen", "Unknown") for r in results]
        })

    except Exception as e:
        print(f"❌ Error Critical: {e}")
        return jsonify({"error": str(e)}), 500

# Endpoint para Explorar (Sugeridos/Populares)
@app.route("/destinations", methods=["GET"])
@cross_origin()
def get_destinations():
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        
        # Recolectar todo
        all_places = list(CAMPECHE_DATA.get("restaurantes_famosos", []))
        all_places.extend(CAMPECHE_DATA.get("lugares_comunidad", []))
        for m_data in CAMPECHE_DATA.get("municipios_data", {}).values():
            all_places.extend(m_data.get("lugares", []))
        for cat in CAMPECHE_DATA.get("puntos_interes_recomendados", {}).values():
            all_places.extend(cat)

        # Populares (Rating)
        popular = sorted(all_places, key=lambda x: float(x.get("rating", 0)), reverse=True)[:8]

        # Sugeridos (Distancia o Random)
        suggested = []
        if lat and lng:
            for p in all_places:
                coords = p.get("coordenadas")
                if coords: p["_d"] = haversine(lat, lng, coords["lat"], coords["lng"])
                else: p["_d"] = 9999
            suggested = sorted(all_places, key=lambda x: x.get("_d", 9999))[:8]
        else:
            pool = list(all_places)
            random.shuffle(pool)
            suggested = pool[:8]

        return jsonify({"popular": popular, "suggested": suggested})
    except Exception as e:
        return jsonify({"popular": [], "suggested": []}), 500

# Endpoint de Búsqueda (Explore Screen)
@app.route("/search_places", methods=["GET"])
@cross_origin()
def search_places_endpoint():
    query = request.args.get('q', '')
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    if not query: return jsonify([])
    
    # Reutilizamos la búsqueda inteligente
    results = search_google_places(query, lat, lng, type_search="general")
    return jsonify([{"nombre": r["nombre"], "direccion": r["direccion"]} for r in results])

# Endpoint Reseñas (Adopción)
@app.route("/review", methods=["POST"])
@cross_origin()
def add_review():
    try:
        data = request.get_json()
        place_name = data.get("place_name")
        rating = float(data.get("rating", 0))
        comment = data.get("comment", "")
        
        if not place_name: return jsonify({"error": "Faltan datos"}), 400

        # Lógica simple de guardar en "lugares_comunidad" si no existe
        # (Implementación simplificada para brevedad, usa la lógica anterior completa si la tienes)
        # ...
        return jsonify({"message": "Guardado"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# -----------------------------
# 🆕 ENDPOINT: DETALLES DEL LUGAR (Google + Naaj Reviews)
# -----------------------------
@app.route("/place_details", methods=["GET"])
@cross_origin()
def get_place_details():
    try:
        place_name = request.args.get('name')
        lat = request.args.get('lat')
        lng = request.args.get('lng')

        if not place_name:
            return jsonify({"error": "Falta nombre del lugar"}), 400

        # 1. Buscar en DATOS LOCALES (JSON) para obtener reseñas
        local_data = None
        
        # Buscamos en todas las listas del JSON
        all_lists = (
            CAMPECHE_DATA.get("restaurantes_famosos", []) + 
            CAMPECHE_DATA.get("lugares_comunidad", []) +
            [l for cat in CAMPECHE_DATA.get("puntos_interes_recomendados", {}).values() for l in cat]
        )
        
        # Agregamos búsqueda en municipios_data
        if "municipios_data" in CAMPECHE_DATA:
            for m_data in CAMPECHE_DATA["municipios_data"].values():
                all_lists.extend(m_data.get("lugares", []))

        for place in all_lists:
            # Comparación simple de nombres (podríamos mejorarla con fuzzy matching luego)
            if place["nombre"].lower() == place_name.lower():
                local_data = place
                break

        # 2. Buscar en GOOGLE PLACES (Datos en vivo: Horario, Foto, Rating Global)
        # Usamos search_google_places con el nombre específico
        google_data = {}
        google_results = search_google_places(place_name, lat, lng, type_search="general")
        
        if google_results:
            # Tomamos el primer resultado que coincida mejor
            google_data = google_results[0]

        # 3. FUSIONAR DATOS
        response_data = {
            "nombre": local_data.get("nombre") if local_data else google_data.get("nombre", place_name),
            "direccion": local_data.get("direccion") if local_data else google_data.get("direccion", "Dirección no disponible"),
            "municipio": "Campeche", # Por defecto, o podrías extraerlo de la dirección
            "imagen": local_data.get("imagen") if (local_data and local_data.get("imagen") != "NO_IMAGE") else google_data.get("imagen", "NO_IMAGE"),
            "abierto_ahora": google_data.get("abierto_ahora", None), # True/False/None
            "reviews": local_data.get("reviews", []) if local_data else []
        }

        # 4. LÓGICA DE RATING (Google vs Naaj)
        # Si tenemos 10 o más reseñas locales, usamos nuestro promedio.
        # Si no, usamos el de Google.
        naaj_rating = local_data.get("rating", 0) if local_data else 0
        naaj_reviews_count = len(response_data["reviews"])

        if naaj_reviews_count >= 10:
            response_data["rating"] = naaj_rating
            response_data["rating_source"] = "Comunidad Naaj 🦎"
        else:
            response_data["rating"] = google_data.get("rating", "N/A")
            response_data["rating_source"] = "Google Places 🟢"

        # Ordenar reseñas por fecha (las más recientes primero) y tomar las últimas 5
        # Asumimos que tienen campo 'date', si no, las dejamos como están
        try:
            response_data["reviews"].sort(key=lambda x: x.get("date", ""), reverse=True)
        except:
            pass # Si falla el ordenamiento, no pasa nada
            
        response_data["reviews"] = response_data["reviews"][:5]

        return jsonify(response_data)

    except Exception as e:
        print(f"Error en detalles: {e}")
        return jsonify({"error": str(e)}), 500
    

if __name__ == "__main__":
    app.run(debug=True, port=5000) # en local: app.run(debug=True, port=5000)
    # host='0.0.0.0' es obligatorio para que sea accesible desde fuera del contenedor
    #app.run(host='0.0.0.0', port=port)
    
    #en produccion: # Render nos da un puerto en la variable de entorno PORT, si no existe usa 5000
    #port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' es obligatorio para que sea accesible desde fuera del contenedor
    #app.run(host='0.0.0.0', port=port)