import os
import requests
from dotenv import load_dotenv

load_dotenv()
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

BASE_URL = "https://maps.googleapis.com/maps/api/place"


def search_places(query, lat=None, lng=None, radius=5000):
    """Búsqueda de lugares usando Places TextSearch o NearbySearch."""

    if lat and lng:
        url = (
            f"{BASE_URL}/nearbysearch/json"
            f"?keyword={query}&location={lat},{lng}&radius={radius}&key={GOOGLE_KEY}"
        )
    else:
        url = (
            f"{BASE_URL}/textsearch/json"
            f"?query={query}+Campeche+México&key={GOOGLE_KEY}"
        )

    data = requests.get(url).json()
    results = data.get("results", [])

    cleaned = []
    for r in results:
        cleaned.append({
            "nombre": r.get("name"),
            "direccion": r.get("formatted_address", r.get("vicinity")),
            "coordenadas": r["geometry"]["location"] if "geometry" in r else None,
            "rating": r.get("rating"),
            "tipo_google": r.get("types"),
            "fuente": "Google Places"
        })

    return cleaned[:5]  # limitar la respuesta


def get_place_details(place_id):
    url = (
        f"{BASE_URL}/details/json?"
        f"place_id={place_id}&key={GOOGLE_KEY}"
    )

    data = requests.get(url).json()
    return data.get("result")
