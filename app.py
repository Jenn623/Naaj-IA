import os
import json
import requests
import urllib.parse
from math import radians, sin, cos, sqrt, atan2
from flask import Flask, request, jsonify, send_from_directory, Response, redirect
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
    """Calcula distancia en KM"""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None: return 9999.0
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def extract_keywords(text):
    """Limpia texto para búsqueda"""
    STOP_WORDS = {"el", "la", "los", "las", "un", "una", "de", "del", "en", "a", "al", "y", "o", "pero", "si", "no", "es", "son", "estoy", "quiero", "quisiera", "recomiendame", "dime", "donde", "hay", "cerca", "lugares", "para", "ir", "hola", "naaj", "gracias", "por", "favor", "que", "tal", "esta", "tan", "busco", "necesito", "tienes", "informacion", "sobre", "cual", "cuales"}
    clean_phrase = re.sub(r'[^\w\s]', '', text.lower())
    return [w for w in clean_phrase.split() if w not in STOP_WORDS and len(w) > 2]

def generate_maps_link(lat, lng, name, address):
    """Link seguro de Google Maps"""
    if lat and lng: return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    query = urllib.parse.quote(f"{name} {address}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"

# -----------------------------
# 3. PROXY DE IMÁGENES (Anti-CORB)
# -----------------------------
@app.route('/image_proxy')
@cross_origin()
def image_proxy():
    ref = request.args.get('ref')
    # Imagen de reserva por defecto si no hay referencia
    fallback = "https://images.unsplash.com/photo-1596130152098-93e71bf4b274?w=500&q=80"
    
    if not ref: return redirect(fallback)
    
    # Pedimos la imagen a Google desde el servidor (Python)
    google_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={ref}&key={GOOGLE_API_KEY}"
    
    try:
        resp = requests.get(google_url, stream=True)
        if resp.status_code == 200:
            # Se la pasamos al frontend tal cual
            return Response(resp.content, mimetype=resp.headers.get('Content-Type'))
        else:
            # Si Google falla (429, 403), usamos fallback silencioso
            return redirect(fallback)
    except:
        return redirect(fallback)

# -----------------------------
# 4. MOTOR DE BÚSQUEDA GOOGLE (Con Proxy)
# -----------------------------
def search_google_places(query, lat=None, lng=None, type_search="general"):
    if not GOOGLE_API_KEY: return []
    base_url = "https://maps.googleapis.com/maps/api/place"
    results = []

    try:
        if lat and lng:
            radius = 2000 if type_search == "utility" else 8000
            url = f"{base_url}/nearbysearch/json?keyword={query}&location={lat},{lng}&radius={radius}&language=es&key={GOOGLE_API_KEY}"
        else:
            suffix = "Mexico" if "campeche" in query.lower() else "Campeche Mexico"
            safe_query = f"{query} {suffix}"
            url = f"{base_url}/textsearch/json?query={safe_query}&language=es&key={GOOGLE_API_KEY}"

        response = requests.get(url)
        data = response.json()

        if "results" in data:
            limit = 5 if type_search == "utility" else 4
            for place in data["results"][:limit]:
                p_lat = place["geometry"]["location"]["lat"]
                p_lng = place["geometry"]["location"]["lng"]
                
                # CONSTRUCCIÓN DE URL CON PROXY
                photo_url = "NO_IMAGE"
                if "photos" in place and len(place["photos"]) > 0:
                    photo_ref = place["photos"][0]["photo_reference"]
                    # Usamos la URL actual del servidor para el proxy
                    try:
                        host_url = request.host_url.rstrip('/')
                        photo_url = f"{host_url}/image_proxy?ref={photo_ref}"
                    except:
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
# 5. RETRIEVER INTELIGENTE
# -----------------------------
def retrieve_smart_data(query, history=[], lat=None, lng=None):
    combined_results = []
    
    # Contexto
    current_keywords = extract_keywords(query)
    follow_up_words = ["eso", "ese", "cual", "como", "donde", "mas", "barato", "caro", "mejor", "opcion", "otro"]
    is_follow_up = any(w in query.lower().split() for w in follow_up_words) or len(current_keywords) == 0
    search_terms = list(current_keywords)
    
    if is_follow_up and history:
        last_user_msg = next((m['text'] for m in reversed(history) if m.get('isUser')), "")
        last_keywords = extract_keywords(last_user_msg)
        search_terms = last_keywords + search_terms

    final_query = " ".join(search_terms) if search_terms else query
    
    # Detección de Municipio
    MUNICIPALITIES = ["calakmul", "calkini", "campeche", "candelaria", "carmen", "champoton", "dzitbalche", "escarcega", "hecelchakan", "hopelchen", "palizada", "seybaplaya", "tenabo"]
    target_municipality = None
    for mun in MUNICIPALITIES:
        if mun in final_query.lower():
            target_municipality = mun
            lat = None; lng = None # Apagamos GPS local
            break

    # Modo Utilidad
    utility_words = ["oxxo", "seven", "tienda", "cajero", "banco", "atm", "hospital", "clinica", "medico", "farmacia", "cruz roja", "policia", "seguridad", "gasolinera"]
    is_utility = any(w in final_query.lower() for w in utility_words)

    if is_utility and lat and lng:
        return search_google_places(final_query, lat, lng, type_search="utility")

    # Búsqueda JSON
    json_hits = []
    seen_names = set()
    lists_to_search = []
    
    if target_municipality and "municipios_data" in CAMPECHE_DATA:
        lists_to_search.extend(CAMPECHE_DATA["municipios_data"].get(target_municipality, {}).get("lugares", []))
    else:
        lists_to_search.extend(CAMPECHE_DATA.get("restaurantes_famosos", []))
        for cat in CAMPECHE_DATA.get("puntos_interes_recomendados", {}).values():
            lists_to_search.extend(cat)
    
    lists_to_search.extend(CAMPECHE_DATA.get("lugares_comunidad", []))

    for item in lists_to_search:
        full_text = f"{item['nombre']} {item.get('categoria','')} {item.get('direccion','')}".lower()
        if any(k in full_text for k in search_terms):
            if "maps_url" not in item:
                coords = item.get("coordenadas")
                if coords: item["maps_url"] = generate_maps_link(coords["lat"], coords["lng"], item["nombre"], "")
                else: item["maps_url"] = generate_maps_link(None, None, item["nombre"], item.get("direccion",""))
            
            item["origen"] = "Datos Naaj 🟠"
            json_hits.append(item)
            seen_names.add(item["nombre"].lower())

    if lat and lng:
        for item in json_hits:
            coords = item.get("coordenadas")
            if coords: item["_dist"] = haversine(lat, lng, coords["lat"], coords["lng"])
            else: item["_dist"] = 9999
        json_hits.sort(key=lambda x: x.get("_dist", 9999))

    combined_results.extend(json_hits[:5])

    # Búsqueda Google Complementaria
    google_triggers = ["abierto", "horario", "autobus", "transporte", "ado", "combi", "colectivo", "valoracion", "rating", "precio", "opiniones"]
    needs_google = len(json_hits) < 2 or any(w in final_query.lower() for w in google_triggers) or target_municipality

    if needs_google and len(final_query) > 2:
        google_hits = search_google_places(final_query, lat, lng, type_search="general")
        for g_item in google_hits:
            if g_item["nombre"].lower() not in seen_names:
                combined_results.append(g_item)
    
    return combined_results or google_hits

# -----------------------------
# 6. PROMPT (Reglas Finales)
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
# 7. ENDPOINTS
# -----------------------------

@app.route("/naaj", methods=["POST"])
def naaj():
    try:
        data = request.get_json()
        question = data.get("question")
        if not question: return jsonify({"error": "No question"}), 400
        
        lat = data.get("lat")
        lng = data.get("lng")
        history = data.get("history", [])

        results = retrieve_smart_data(question, history, lat, lng)
        prompt = build_prompt(question, results, "auto", (lat and lng), history)
        
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
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

        return jsonify({"answer": raw_text, "messages": messages_to_send})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🆕 ENDPOINT DINÁMICO DE DESTINOS (Ruleta Rusa + Proxy)
@app.route("/destinations", methods=["GET"])
@cross_origin()
def get_destinations():
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        
        # 1. Datos Locales
        all_places = list(CAMPECHE_DATA.get("restaurantes_famosos", []))
        for m_data in CAMPECHE_DATA.get("municipios_data", {}).values():
            all_places.extend(m_data.get("lugares", []))
        
        # 2. Datos Frescos de Google (Categoría Sorpresa)
        categories = ["cafeterias bonitas", "tacos populares", "parques tranquilos", "museos", "cenas romanticas", "comida regional"]
        random_cat = random.choice(categories)
        print(f"🎰 Destinos sorpresa: '{random_cat}'")
        
        google_fresh = search_google_places(random_cat, lat, lng)
        
        # 3. Mezclar
        combined = all_places + google_fresh
        unique_places = {p['nombre']: p for p in combined}.values()
        final_list = list(unique_places)
        
        # 4. Ordenar
        popular = sorted(final_list, key=lambda x: float(x.get("rating", 0)), reverse=True)[:8]
        
        if lat and lng:
            for p in final_list:
                coords = p.get("coordenadas") or {}
                if coords.get('lat'): p["_d"] = haversine(lat, lng, coords['lat'], coords['lng'])
                else: p["_d"] = 9999
            suggested = sorted(final_list, key=lambda x: x.get("_d", 9999))[:8]
        else:
            pool = list(final_list)
            random.shuffle(pool)
            suggested = pool[:8]

        return jsonify({"popular": popular, "suggested": suggested})
    except Exception as e:
        print(f"Error destinations: {e}")
        return jsonify({"popular": [], "suggested": []}), 500

@app.route("/search_places", methods=["GET"])
@cross_origin()
def search_places_endpoint():
    query = request.args.get('q', '')
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    if not query: return jsonify([])
    results = search_google_places(query, lat, lng, type_search="general")
    return jsonify(results)

@app.route("/review", methods=["POST"])
@cross_origin()
def add_review():
    return jsonify({"message": "Guardado (Demo)"})

@app.route("/place_details", methods=["GET"])
@cross_origin()
def get_place_details():
    place_name = request.args.get('name')
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    
    # Busca en JSON o Google
    # (Simplificado para copiar, usa tu lógica completa si la tienes)
    # ...
    # Reutilizamos search para detalle rápido
    results = search_google_places(place_name, lat, lng)
    if results: return jsonify(results[0])
    return jsonify({}) 

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000)) # en local: app.run(debug=True, port=5000)
    # host='0.0.0.0' es obligatorio para que sea accesible desde fuera del contenedor
    app.run(host='0.0.0.0', port=port)
    
    #en produccion: # Render nos da un puerto en la variable de entorno PORT, si no existe usa 5000
    #port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' es obligatorio para que sea accesible desde fuera del contenedor
    #app.run(host='0.0.0.0', port=port)