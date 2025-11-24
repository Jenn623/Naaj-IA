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
import pytz # 🆕 Librería para Zona Horaria
import random
import re

# -----------------------------
# 1. CONFIGURACIÓN
# -----------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# 🆕 Nuevas llaves para la base de datos JSONBin
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")

genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app)

# -----------------------------
# 🆕 GESTIÓN DE DATOS EN LA NUBE (JSONBIN)
# -----------------------------
def load_data():
    """Carga los datos desde JSONBin. Si falla, usa el archivo local."""
    print("☁️ Cargando datos desde la nube...")
    
    if not JSONBIN_API_KEY or not JSONBIN_BIN_ID:
        print("⚠️ Faltan credenciales de JSONBin. Usando modo local.")
        return load_local_data()

    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # JSONBin devuelve los datos dentro de la llave "record"
            data = response.json().get("record", {})
            print("✅ Datos cargados exitosamente desde JSONBin.")
            return data
        else:
            print(f"⚠️ Error cargando nube ({response.status_code}). Usando local.")
            return load_local_data()
    except Exception as e:
        print(f"❌ Error conexión nube: {e}")
        return load_local_data()

def load_local_data():
    """Carga datos del archivo local como respaldo."""
    try:
        with open("campeche.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ ALERTA: campeche.json no encontrado. Iniciando vacío.")
        return {"municipios_data": {}, "restaurantes_famosos": [], "lugares_comunidad": []}

def save_data_cloud(data):
    """Guarda los cambios en JSONBin para persistencia real."""
    if not JSONBIN_API_KEY or not JSONBIN_BIN_ID:
        print("⚠️ No se puede guardar en la nube: Faltan credenciales.")
        return

    print("☁️ Guardando cambios en la nube...")
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": JSONBIN_API_KEY
    }
    
    try:
        # PUT actualiza el contenido del Bin existente
        response = requests.put(url, json=data, headers=headers)
        if response.status_code == 200:
            print("✅ Base de datos actualizada en JSONBin.")
        else:
            print(f"⚠️ Error al guardar en JSONBin: {response.status_code}")
    except Exception as e:
        print(f"❌ Error guardando en nube: {e}")

# Carga Inicial (Variable Global en Memoria)
CAMPECHE_DATA = load_data()

# -----------------------------
# 2. UTILIDADES
# -----------------------------
def get_mexico_time():
    """Obtiene la fecha y hora exacta de CDMX"""
    try:
        tz = pytz.timezone('America/Mexico_City')
        return datetime.now(tz)
    except Exception:
        return datetime.now() # Fallback si pytz falla

def haversine(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None: return 9999.0
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def extract_keywords(text):
    STOP_WORDS = {"el", "la", "los", "las", "un", "una", "de", "del", "en", "a", "al", "y", "o", "pero", "si", "no", "es", "son", "estoy", "quiero", "quisiera", "recomiendame", "dime", "donde", "hay", "cerca", "lugares", "para", "ir", "hola", "naaj", "gracias", "por", "favor", "que", "tal", "esta", "tan", "busco", "necesito", "tienes", "informacion", "sobre", "cual", "cuales"}
    clean_phrase = re.sub(r'[^\w\s]', '', text.lower())
    return [w for w in clean_phrase.split() if w not in STOP_WORDS and len(w) > 2]

def generate_maps_link(lat, lng, name, address):
    if lat and lng: return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    query = urllib.parse.quote(f"{name} {address}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"

# -----------------------------
# 3. FUNCIONES DE GOOGLE
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
                
                photo_url = "NO_IMAGE"
                if "photos" in place and len(place["photos"]) > 0:
                    try:
                        host_url = request.host_url.rstrip('/')
                        photo_ref = place["photos"][0]["photo_reference"]
                        photo_url = f"{host_url}/image_proxy?ref={photo_ref}"
                    except: pass

                place_data = {
                    "place_id": place.get("place_id"),
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
        print(f"❌ Error Google Search: {e}")

    return results

def get_google_place_details(place_id):
    if not GOOGLE_API_KEY: return {}
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,rating,formatted_address,opening_hours,photos,geometry&language=es&key={GOOGLE_API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if "result" in data:
            res = data["result"]
            photo_url = "NO_IMAGE"
            if "photos" in res and len(res["photos"]) > 0:
                try:
                    host_url = request.host_url.rstrip('/')
                    photo_ref = res["photos"][0]["photo_reference"]
                    photo_url = f"{host_url}/image_proxy?ref={photo_ref}"
                except: pass

            return {
                "nombre": res.get("name"),
                "direccion": res.get("formatted_address"),
                "rating": res.get("rating", "N/A"),
                "abierto_ahora": res.get("opening_hours", {}).get("open_now", None),
                "horario_texto": res.get("opening_hours", {}).get("weekday_text", []),
                "imagen": photo_url,
                "coordenadas": res["geometry"]["location"]
            }
    except: pass
    return {}

# -----------------------------
# 4. PROXY Y ENDPOINTS
# -----------------------------
@app.route('/image_proxy')
@cross_origin()
def image_proxy():
    ref = request.args.get('ref')
    fallback = "https://images.unsplash.com/photo-1596130152098-93e71bf4b274?w=500&q=80"
    if not ref: return redirect(fallback)
    
    google_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={ref}&key={GOOGLE_API_KEY}"
    try:
        resp = requests.get(google_url, stream=True)
        if resp.status_code == 200:
            return Response(resp.content, mimetype=resp.headers.get('Content-Type'))
        else: return redirect(fallback)
    except: return redirect(fallback)

@app.route("/place_details", methods=["GET"])
@cross_origin()
def get_place_details():
    try:
        place_name = request.args.get('name')
        lat = request.args.get('lat')
        lng = request.args.get('lng')
        if not place_name: return jsonify({"error": "Falta nombre"}), 400

        local_data = None
        all_lists = list(CAMPECHE_DATA.get("restaurantes_famosos", []))
        all_lists.extend(CAMPECHE_DATA.get("lugares_comunidad", []))
        for m_data in CAMPECHE_DATA.get("municipios_data", {}).values():
            all_lists.extend(m_data.get("lugares", []))
        for cat in CAMPECHE_DATA.get("puntos_interes_recomendados", {}).values():
            all_lists.extend(cat)

        for place in all_lists:
            if place["nombre"].lower().strip() == place_name.lower().strip():
                local_data = place
                break

        google_details = {}
        search_results = search_google_places(place_name, lat, lng)
        if search_results:
            best_match = search_results[0]
            place_id = best_match.get("place_id")
            if place_id:
                google_details = get_google_place_details(place_id)
            else:
                google_details = best_match

        response_data = {
            "nombre": local_data.get("nombre") if local_data else google_details.get("nombre", place_name),
            "direccion": google_details.get("direccion") or local_data.get("direccion", "Dirección no disponible"),
            "imagen": google_details.get("imagen") if google_details.get("imagen") != "NO_IMAGE" else local_data.get("imagen", "NO_IMAGE"),
            "abierto_ahora": google_details.get("abierto_ahora", None),
            "horario_texto": google_details.get("horario_texto", []),
            "reviews": local_data.get("reviews", []) if local_data else []
        }

        naaj_rating = local_data.get("rating", 0) if local_data else 0
        if len(response_data["reviews"]) >= 5:
            response_data["rating"] = naaj_rating
            response_data["rating_source"] = "Comunidad Naaj 🦎"
        else:
            response_data["rating"] = google_details.get("rating", "N/A")
            response_data["rating_source"] = "Google Places 🟢"

        response_data["reviews"].sort(key=lambda x: x.get("date", ""), reverse=True)
        response_data["reviews"] = response_data["reviews"][:10]

        return jsonify(response_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/review", methods=["POST"])
@cross_origin()
def add_review():
    try:
        data = request.get_json()
        place_name = data.get("place_name")
        user_rating = float(data.get("rating", 0))
        comment = data.get("comment", "")
        address = data.get("address", "")
        coords = data.get("coords", None)
        category = data.get("category", "Lugar Recomendado")

        if not place_name: return jsonify({"error": "Faltan datos"}), 400

        global CAMPECHE_DATA
        
        target_place = None
        all_lists = [CAMPECHE_DATA.get("restaurantes_famosos", []), CAMPECHE_DATA.get("lugares_comunidad", [])]
        for m in CAMPECHE_DATA.get("municipios_data", {}).values(): all_lists.append(m.get("lugares", []))
        for c in CAMPECHE_DATA.get("puntos_interes_recomendados", {}).values(): all_lists.append(c)

        for lst in all_lists:
            for p in lst:
                if p["nombre"] == place_name:
                    target_place = p
                    break
            if target_place: break

        if not target_place:
            print(f"🆕 Nuevo lugar: {place_name}")
            new_place = {
                "nombre": place_name,
                "categoria": category,
                "direccion": address,
                "coordenadas": coords,
                "rating": user_rating,
                "reviews": [],
                "origen": "Comunidad 👥",
                "imagen": "NO_IMAGE"
            }
            # Asegurarse de que la lista exista
            if "lugares_comunidad" not in CAMPECHE_DATA:
                CAMPECHE_DATA["lugares_comunidad"] = []
            
            CAMPECHE_DATA["lugares_comunidad"].append(new_place)
            target_place = new_place

        # Agregar reseña con fecha local
        new_review = {
            "user": "Viajero Explorador",
            "rating": user_rating,
            "comment": comment,
            "date": get_mexico_time().strftime("%Y-%m-%d %H:%M")
        }
        
        if "reviews" not in target_place: target_place["reviews"] = []
        target_place["reviews"].insert(0, new_review)

        vals = [r["rating"] for r in target_place["reviews"]]
        target_place["rating"] = round(sum(vals) / len(vals), 1)

        # 🆕 GUARDADO EN LA NUBE (JSONBin)
        save_data_cloud(CAMPECHE_DATA)

        return jsonify({"message": "Guardado", "new_rating": target_place["rating"]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/search_places", methods=["GET"])
@cross_origin()
def search_places_endpoint():
    q = request.args.get('q',''); lat = request.args.get('lat'); lng = request.args.get('lng')
    if not q: return jsonify([])
    return jsonify([{"nombre":r["nombre"],"direccion":r["direccion"]} for r in search_google_places(q,lat,lng)])

@app.route("/destinations", methods=["GET"])
@cross_origin()
def get_destinations():
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        
        all_places = list(CAMPECHE_DATA.get("restaurantes_famosos", []))
        for m_data in CAMPECHE_DATA.get("municipios_data", {}).values():
            all_places.extend(m_data.get("lugares", []))
        all_places.extend(CAMPECHE_DATA.get("lugares_comunidad", []))
        
        categories = ["cafeterias bonitas", "tacos populares", "parques tranquilos", "museos", "cenas romanticas", "comida regional"]
        random_cat = random.choice(categories)
        
        google_fresh = search_google_places(random_cat, lat, lng)
        
        combined = all_places + google_fresh
        unique_places = {p['nombre']: p for p in combined}.values()
        final_list = list(unique_places)
        
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
        return jsonify({"popular": [], "suggested": []}), 500

def retrieve_smart_data(query, history=[], lat=None, lng=None):
    combined_results = []
    current_keywords = extract_keywords(query)
    follow_up_words = ["eso", "ese", "cual", "como", "donde", "mas", "barato", "caro", "mejor", "opcion", "otro"]
    is_follow_up = any(w in query.lower().split() for w in follow_up_words) or len(current_keywords) == 0
    search_terms = list(current_keywords)
    
    if is_follow_up and history:
        last_user_msg = next((m['text'] for m in reversed(history) if m.get('isUser')), "")
        last_keywords = extract_keywords(last_user_msg)
        search_terms = last_keywords + search_terms

    final_query = " ".join(search_terms) if search_terms else query
    
    MUNICIPALITIES = ["calakmul", "calkini", "campeche", "candelaria", "carmen", "champoton", "dzitbalche", "escarcega", "hecelchakan", "hopelchen", "palizada", "seybaplaya", "tenabo"]
    target_municipality = None
    for mun in MUNICIPALITIES:
        if mun in final_query.lower():
            target_municipality = mun
            lat = None; lng = None
            break

    utility_words = ["oxxo", "seven", "tienda", "cajero", "banco", "atm", "hospital", "clinica", "medico", "farmacia", "cruz roja", "policia", "seguridad", "gasolinera"]
    is_utility = any(w in final_query.lower() for w in utility_words)

    if is_utility and lat and lng:
        return search_google_places(final_query, lat, lng, type_search="utility")

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

    google_triggers = ["abierto", "horario", "autobus", "transporte", "ado", "combi", "colectivo", "valoracion", "rating", "precio", "opiniones"]
    needs_google = len(json_hits) < 2 or any(w in final_query.lower() for w in google_triggers) or target_municipality

    if needs_google and len(final_query) > 2:
        google_hits = search_google_places(final_query, lat, lng, type_search="general")
        for g_item in google_hits:
            if g_item["nombre"].lower() not in seen_names:
                combined_results.append(g_item)
    
    return combined_results or google_hits

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

4. **FORMATTING:**
   - **Chat/Casual:** Just text.
   - **Recommendations:** Use the 3-part format:
     [Details] ||| [IMAGE_URL_OR_NO_IMAGE] ||| [Address] [maps_url]
     
   *Note:* For lists, put all addresses in Part 3. Do not break the 3-part structure.
"""

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000)) # en local: app.run(debug=True, port=5000)
    # host='0.0.0.0' es obligatorio para que sea accesible desde fuera del contenedor
    app.run(host='0.0.0.0', port=port)
    
    #en produccion: # Render nos da un puerto en la variable de entorno PORT, si no existe usa 5000
    #port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' es obligatorio para que sea accesible desde fuera del contenedor
    #app.run(host='0.0.0.0', port=port)