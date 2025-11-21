import os
import json
from math import radians, sin, cos, sqrt, atan2
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
from langdetect import detect

# -----------------------------
# CONFIGURACIÓN INICIAL
# -----------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app)

# -----------------------------
# CARGAR DATASET DE CAMPECHE
# -----------------------------
with open("campeche.json", "r", encoding="utf-8") as f:
    CAMPECHE_DATA = json.load(f)

# -----------------------------
# FUNCIÓN HAVERSINE (distancia)
# -----------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

# -----------------------------
# RETRIEVER BÁSICO
# -----------------------------
def retrieve_relevant_data(query, lat=None, lng=None):
    query_low = query.lower()
    results = []

    # 1. Buscar en restaurantes famosos
    for item in CAMPECHE_DATA.get("restaurantes_famosos", []):
        if query_low in item["nombre"].lower() or query_low in item["categoria"].lower():
            results.append(item)

    # 2. Buscar en dulces típicos
    for item in CAMPECHE_DATA["puntos_interes_recomendados"].get("dulces_tipicos", []):
        if query_low in item["nombre"].lower():
            results.append(item)

    # 3. Buscar en puntos históricos
    for item in CAMPECHE_DATA["puntos_interes_recomendados"].get("historia_y_cultura", []):
        if query_low in item["nombre"].lower():
            results.append(item)

    # Si el usuario envía coordenadas, ordenamos por distancia
    if lat and lng:
        for r in results:
            coords = r.get("coordenadas")
            if coords:
                r["distance_km"] = round(haversine(lat, lng, coords["lat"], coords["lng"]), 2)
            else:
                r["distance_km"] = 9999
        results.sort(key=lambda x: x["distance_km"])

    return results[:5]

# -----------------------------
# 🆕 CONSTRUIR PROMPT CON MEMORIA
# -----------------------------
def build_prompt(user_question, retrieved_data, user_lang, has_coords, history):
    location_status = "User Location Provided (GPS)" if has_coords else "Unknown Location"

    # 1. Formatear el historial para que Gemini lo lea como un guion
    # Convertimos la lista de objetos en texto plano:
    # User: ...
    # Naaj: ...
    history_text = ""
    # Tomamos solo los últimos 6 mensajes para no saturar (3 turnos)
    recent_history = history[-6:] 
    
    for msg in recent_history:
        role = "User" if msg.get('isUser') else "Naaj"
        content = msg.get('text', '')
        history_text += f"{role}: {content}\n"

    # 2. Prompt Principal (Mantenemos identidad y reglas)
    return f"""
You are *Naaj-IA*, an intelligent, friendly and culturally aware tourism assistant for Mexico.
You are currently specialized in the state of Campeche.
Current User Location Status: {location_status}

LANGUAGE TO USE: {user_lang}

--- PREVIOUS CONVERSATION HISTORY ---
(Use this context to understand what the user is asking for now)
{history_text}
-------------------------------------

CURRENT USER QUESTION: "{user_question}"

RELEVANT DATA (JSON):
{json.dumps(retrieved_data, ensure_ascii=False, indent=2)}

--- INSTRUCTIONS FOR BEHAVIOR ---

1. **CONTEXT RULE (CRITICAL):** - If the user asks for recommendations AND you do NOT have their location (Status: Unknown Location) AND they did not specify an area:
   - CHECK HISTORY FIRST: If the user *just* provided their location in the previous message, proceed to recommend.
   - IF NO CONTEXT: Kindly ask: "To give you the best options, could you tell me where you are located or which area you are close to?"

2. **SELECTION RULE:**
   - If the user explicitly selects a place, format response in 3 parts separated by "|||":
   - [Affirmation] ||| [Place Name for Image] ||| [Address/Map Link]

3. **GENERAL RULES:**
   - Always be respectful, warm, and helpful (Mexican hospitality).
   - Do NOT invent information. If you don't know, admit it politely or suggest a general option.
   - NEVER mix languages. Respond only in {user_lang}.
"""

# -----------------------------
# ENDPOINT PRINCIPAL: /naaj
# -----------------------------
@app.route("/naaj", methods=["POST"])
def naaj():
    try:
        data = request.get_json()
        user_question = data.get("question")
        user_lat = data.get("lat")
        user_lng = data.get("lng")
        # 🆕 Recibimos el historial del frontend
        history = data.get("history", []) 

        has_coords = True if (user_lat and user_lng) else False

        if not user_question:
            return jsonify({"error": "Se requiere una pregunta."}), 400

        user_lang = detect(user_question)
        
        # OJO: Aquí hay un truco. Si el usuario dice "estoy en el centro", 
        # retrieve_relevant_data no encontrará "mariscos" porque la query cambió.
        # En una implementación avanzada, usaríamos el historial para buscar en el JSON.
        # Por ahora, mantenemos la búsqueda simple con la pregunta actual.
        retrieved = retrieve_relevant_data(user_question, user_lat, user_lng)

        # 🆕 Pasamos el historial al prompt
        prompt = build_prompt(user_question, retrieved, user_lang, has_coords, history)

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        
        raw_text = response.text

        # Procesamiento de respuesta triple (Igual que antes)
        messages_to_send = []
        if "|||" in raw_text:
            parts = raw_text.split("|||")
            if len(parts) > 0: messages_to_send.append({"type": "text", "content": parts[0].strip()})
            if len(parts) > 1: 
                place_query = parts[1].strip().replace(" ", "+")
                messages_to_send.append({"type": "image", "content": f"https://www.google.com/maps/search/?api=1&query={place_query}", "alt_text": parts[1].strip()})
            if len(parts) > 2: messages_to_send.append({"type": "text", "content": parts[2].strip()})
        else:
            messages_to_send.append({"type": "text", "content": raw_text})

        return jsonify({
            "answer": raw_text,
            "messages": messages_to_send
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=3000)