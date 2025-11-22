import os
import json
from math import radians, sin, cos, sqrt, atan2
from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS, cross_origin
from dotenv import load_dotenv
import google.generativeai as genai
from langdetect import detect, LangDetectException # 🆕 Importamos la excepción
import re

# -----------------------------
# CONFIGURACIÓN INICIAL
# -----------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
CORS(app)

with open("campeche.json", "r", encoding="utf-8") as f:
    CAMPECHE_DATA = json.load(f)

# -----------------------------
# UTILIDADES (Distancia y Limpieza)
# -----------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def extract_keywords(text_list):
    STOP_WORDS = {
        "el", "la", "los", "las", "un", "una", "unos", "unas", 
        "de", "del", "en", "a", "al", "con", "sin", "por", "para",
        "y", "o", "pero", "si", "no", "es", "son", "estoy", "estas",
        "recomiendame", "quisiera", "busco", "quiero", "dime", "cerca",
        "lugar", "lugares", "donde", "puedo", "comer", "ir", "visitar",
        "hola", "gracias", "naaj", "favor", "tienes", "algun", "alguna", "hay"
    }
    keywords = set()
    for phrase in text_list:
        words = re.findall(r'\w+', phrase.lower())
        for w in words:
            if w not in STOP_WORDS and len(w) > 2:
                keywords.add(w)
    return list(keywords)

# -----------------------------
# RETRIEVER (Buscador)
# -----------------------------
def retrieve_relevant_data(current_query, history=[], lat=None, lng=None):
    results = []
    seen_ids = set()

    raw_phrases = [current_query]
    if history:
        user_msgs = [msg['text'] for msg in reversed(history) if msg.get('isUser')]
        raw_phrases.extend(user_msgs[:2])

    search_keywords = extract_keywords(raw_phrases)
    print(f"🔍 Palabras clave: {search_keywords}")

    for keyword in search_keywords:
        # Búsqueda general en todas las categorías del JSON
        # A. Restaurantes
        for item in CAMPECHE_DATA.get("restaurantes_famosos", []):
            text_to_search = f"{item['nombre']} {item['categoria']}".lower()
            if keyword in text_to_search and item["nombre"] not in seen_ids:
                results.append(item)
                seen_ids.add(item["nombre"])

        # B. Dulces y Puntos de Interés
        puntos = CAMPECHE_DATA.get("puntos_interes_recomendados", {})
        for category in puntos.values():
            for item in category:
                if keyword in item["nombre"].lower() and item["nombre"] not in seen_ids:
                    results.append(item)
                    seen_ids.add(item["nombre"])

    if lat and lng:
        for r in results:
            coords = r.get("coordenadas")
            if coords:
                r["distance_km"] = round(haversine(lat, lng, coords["lat"], coords["lng"]), 2)
            else:
                r["distance_km"] = 9999
        results.sort(key=lambda x: x["distance_km"])

    return results[:8]

# -----------------------------
# 🆕 PROMPT REFORZADO PARA IDIOMA
# -----------------------------
def build_prompt(user_question, retrieved_data, user_lang, has_coords, history):
    location_status = "User Location Provided (GPS)" if has_coords else "Unknown Location"
    
    history_text = ""
    for msg in history[-4:]:
        role = "User" if msg.get('isUser') else "Naaj"
        content = msg.get('text', '')
        history_text += f"{role}: {content}\n"

    # Mapeo simple para que la IA entienda mejor el código ISO
    lang_map = {"es": "Spanish", "en": "English", "fr": "French", "de": "German"}
    full_lang_name = lang_map.get(user_lang, user_lang)

    return f"""
You are *Naaj-IA*, an intelligent, friendly and culturally aware tourism assistant for Mexico.
You are currently specialized in the state of Campeche.

--- CONTEXT & DATA ---
User Location: {location_status}
History:
{history_text}

Current Question: "{user_question}"

Data Found (JSON):
{json.dumps(retrieved_data, ensure_ascii=False, indent=2)}

--- INSTRUCTIONS ---
1. Analyze the History and Question to understand user intent.
2. Use the JSON data to provide accurate recommendations.
3. If JSON has an "imagen" URL, use it.
4. If recommending, format as: [Affirmation] ||| [IMAGE_URL] ||| [Address/Link]

--- CRITICAL LANGUAGE RULE ---
The user is speaking in: **{full_lang_name} ({user_lang})**.
You MUST respond EXCLUSIVELY in **{full_lang_name}**.
Do NOT write in English unless the user asked in English.
Translate any internal reasoning to {full_lang_name} before outputting.

RESPONSE STARTS HERE ({full_lang_name}):
"""

# -----------------------------
# RUTA IMÁGENES
# -----------------------------
@app.route('/imagenes-naaj/<path:filename>')
@cross_origin()
def serve_image(filename):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_dir = os.path.join(base_dir, 'static', 'images')
        return send_from_directory(image_dir, filename)
    except Exception as e:
        return jsonify({"error": "Imagen no encontrada"}), 404

# -----------------------------
# ENDPOINT PRINCIPAL
# -----------------------------
@app.route("/naaj", methods=["POST"])
def naaj():
    try:
        data = request.get_json()
        user_question = data.get("question")
        user_lat = data.get("lat")
        user_lng = data.get("lng")
        history = data.get("history", [])

        has_coords = True if (user_lat and user_lng) else False
        if not user_question: return jsonify({"error": "Falta pregunta"}), 400

        # 🆕 DETECCIÓN ROBUSTA DE IDIOMA
        try:
            user_lang = detect(user_question)
        except LangDetectException:
            # Si falla (ej. texto vacío o números), usamos español por defecto
            user_lang = "es"

        # Recuperar datos
        retrieved = retrieve_relevant_data(user_question, history, user_lat, user_lng)

        # Construir prompt
        prompt = build_prompt(user_question, retrieved, user_lang, has_coords, history)

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        raw_text = response.text

        # Lógica de respuesta triple
        messages_to_send = []
        if "|||" in raw_text:
            parts = raw_text.split("|||")
            if len(parts) > 0: messages_to_send.append({"type": "text", "content": parts[0].strip()})
            if len(parts) > 1: 
                # Si Gemini manda "NO_IMAGE", respetamos eso. Si manda URL, la pasamos.
                img_content = parts[1].strip()
                if "http" in img_content:
                    messages_to_send.append({"type": "image", "content": img_content, "alt_text": "Recomendación Naaj"})
            if len(parts) > 2: messages_to_send.append({"type": "text", "content": parts[2].strip()})
        else:
            messages_to_send.append({"type": "text", "content": raw_text})

        return jsonify({
            "answer": raw_text,
            "messages": messages_to_send,
            "detected_lang": user_lang
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)