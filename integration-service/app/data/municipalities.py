"""DIAN municipality codes for Colombia — top 50 cities."""

MUNICIPALITIES = {
    "bogota": 149, "bogotá": 149, "bogota d.c.": 149, "bogotá d.c.": 149, "bogotá, d.c.": 149,
    "medellin": 5001, "medellín": 5001,
    "cali": 76001,
    "barranquilla": 8001,
    "cartagena": 13001,
    "cucuta": 54001, "cúcuta": 54001,
    "bucaramanga": 68001,
    "pereira": 66001,
    "santa marta": 47001,
    "ibague": 73001, "ibagué": 73001,
    "pasto": 52001,
    "manizales": 17001,
    "neiva": 41001,
    "villavicencio": 50001,
    "armenia": 63001,
    "valledupar": 20001,
    "monteria": 23001, "montería": 23001,
    "sincelejo": 70001,
    "popayan": 19001, "popayán": 19001,
    "florencia": 18001,
    "tunja": 15001,
    "riohacha": 44001,
    "quibdo": 27001, "quibdó": 27001,
    "yopal": 85001,
    "mocoa": 86001,
    "leticia": 91001,
    "inirida": 94001, "inírida": 94001,
    "puerto carreño": 99001, "puerto carreño": 99001,
    "mitu": 97001, "mitú": 97001,
    "san jose del guaviare": 95001, "san josé del guaviare": 95001,
    "arauca": 81001,
    "sogamoso": 15759,
    "duitama": 15238,
    "girardot": 25307,
    "palmira": 76520,
    "buga": 76111,
    "tulua": 76834, "tuluá": 76834,
    "cartago": 76147,
    "dosquebradas": 66170,
    "envigado": 5266,
    "itagui": 5360, "itagüí": 5360,
    "bello": 5088,
    "rionegro": 5615,
    "sabaneta": 5631,
    "soledad": 8758,
    "soacha": 25754,
    "chia": 25175, "chía": 25175,
    "zipaquira": 25899, "zipaquirá": 25899,
    "fusagasuga": 25290, "fusagasugá": 25290,
    "facatativa": 25269, "facatativá": 25269,
}


def resolve_municipality_id(city_name: str) -> int:
    """Resolve a city name to its DIAN municipality ID. Returns 149 (Bogotá) as default."""
    if not city_name:
        return 149
    normalized = city_name.strip().lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    # Try exact match first
    if normalized in MUNICIPALITIES:
        return MUNICIPALITIES[normalized]
    # Try with accents
    lower = city_name.strip().lower()
    if lower in MUNICIPALITIES:
        return MUNICIPALITIES[lower]
    # Try partial match
    for key, code in MUNICIPALITIES.items():
        if key in normalized or normalized in key:
            return code
    return 149  # Default to Bogotá
