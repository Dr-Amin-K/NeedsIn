# Canonical locations with coordinates
LOCATION_COORDS = {
    "Khartoum": (15.5007, 32.5599),
    "Omdurman": (15.6445, 32.4777),
    "Bahri": (15.6594, 32.5523),
    "Port Sudan": (19.6158, 37.2116),
    "El Obeid": (13.1833, 30.2167),
    "Nyala": (12.0566, 24.8880),
    "El Fasher": (13.6279, 25.3494),
    "Kassala": (15.4500, 36.4000),
    "Gedaref": (14.0333, 35.3833),
    "Atbara": (17.7022, 33.9864),
    "Dongola": (19.1667, 30.4833),
    "Kosti": (13.1667, 32.6667),
    "Sennar": (13.5667, 33.5667),
    "Wad Madani": (14.4012, 33.5217),
    "Shendi": (16.6800, 33.4200),
}

# English → Canonical location
ENGLISH_VARIANTS = {
    "khartoum": "Khartoum",
    "omdurman": "Omdurman",
    "bahri": "Bahri",
    "port sudan": "Port Sudan",
    "portsudan": "Port Sudan",
    "el obeid": "El Obeid",
    "al obeid": "El Obeid",
    "obeid": "El Obeid",
    "nyala": "Nyala",
    "el fasher": "El Fasher",
    "al fasher": "El Fasher",
    "fashir": "El Fasher",
    "kassala": "Kassala",
    "gedaref": "Gedaref",
    "gadaref": "Gedaref",
    "atbara": "Atbara",
    "dongola": "Dongola",
    "kosti": "Kosti",
    "sennar": "Sennar",
    "wad madani": "Wad Madani",
    "medani": "Wad Madani",
    "madani": "Wad Madani",
    "shendi": "Shendi",
}

# Arabic → Canonical location
ARABIC_VARIANTS = {
    "الخرطوم": "Khartoum",
    "أم درمان": "Omdurman",
    "أمدرمان": "Omdurman",
    "امدرمان": "Omdurman",
    "ام درمان": "Omdurman",
    "بحري": "Bahri",
    "بورتسودان": "Port Sudan",
    "بورسودان": "Port Sudan",
    "بورت سودان": "Port Sudan",
    "الأبيض": "El Obeid",
    "الابيض": "El Obeid",
    "نيالا": "Nyala",
    "الفاشر": "El Fasher",
    "كسلا": "Kassala",
    "القضارف": "Gedaref",
    "عطبرة": "Atbara",
    "عطبره": "Atbara",
    "دنقلا": "Dongola",
    "الدمازين": "Damazin",
    "كوستي": "Kosti",
    "سنار": "Sennar",
    "ود مدني": "Wad Madani",
    "مدني": "Wad Madani",
    "شندي": "Shendi",
}

# Merge all searchable variants
SEARCH_INDEX = {
    **{k.lower(): v for k, v in ENGLISH_VARIANTS.items()},
    **{k: v for k, v in ARABIC_VARIANTS.items()},
}

def extract_location(text: str) -> str | None:
    """
    Detect a Sudanese city name (English or Arabic) in text.
    Returns canonical city name or None.
    """
    if not text:
        return None

    s = text.lower()

    # English search
    for key, city in ENGLISH_VARIANTS.items():
        if key in s:
            return city, LOCATION_COORDS[city]


    # Arabic search (case-sensitive)
    for key, city in ARABIC_VARIANTS.items():
        if key in text:
            return city, LOCATION_COORDS[city]

    return None
