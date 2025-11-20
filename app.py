import os
import json
from math import radians, sin, cos, sqrt, atan2
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai

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

    # 1️⃣ Buscar en restaurantes famosos
    for item in CAMPECHE_DATA.get("restaurantes_famosos", []):
        if query_low in item["nombre"].lower() or query_low in item["categoria"].lower():
            results.append(item)

    # 2️⃣ Buscar en dulces típicos
    for item in CAMPECHE_DATA["puntos_interes_recomendados"].get("dulces_tipicos", []):
        if query_low in item["nombre"].lower():
            results.append(item)

    # 3️⃣ Buscar en puntos históricos
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

    return results[:5]  # máximo 5 resultados


# -----------------------------
# CONSTRUIR PROMPT PARA GEMINI
# -----------------------------
def build_prompt(user_question, retrieved_data):
    return f"""
Eres Naaj-IA, un asistente turístico inteligente, amable y culturalmente consciente.
Hablas TODOS los idiomas y SIEMPRE respondes en el mismo idioma que el usuario.
Tu especialidad es México, especialmente Campeche, su cultura, lugares turísticos y transporte.

PREGUNTA DEL USUARIO:
{user_question}

DATOS RELEVANTES DEL DATASET:
{json.dumps(retrieved_data, ensure_ascii=False, indent=2)}

INSTRUCCIONES:
- Determina automáticamente el idioma del usuario y responde exclusivamente en ese idioma.
- Usa SOLO los datos proporcionados si aplican.
- Si el tema no aparece en los datos, responde con conocimiento general turístico.
- Da recomendaciones prácticas y fáciles de seguir.
- Si el usuario pide lugares cercanos, prioriza los que tengan 'distance_km'.
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

        if not user_question:
            return jsonify({"error": "Se requiere una pregunta."}), 400

        # 1️⃣ Recuperación de datos relevantes
        retrieved = retrieve_relevant_data(user_question, user_lat, user_lng)

        # 2️⃣ Construir prompt
        prompt = build_prompt(user_question, retrieved)

        # 3️⃣ Configurar modelo Gemini
        model = genai.GenerativeModel("gemini-2.5-flash")

        response = model.generate_content(prompt)

        return jsonify({
            "question": user_question,
            "retrieved_data": retrieved,
            "answer": response.text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------
# INICIAR SERVIDOR
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=3000)
