"""
kultur· API Modul v2 – 100% KOSTENLOS
======================================
- OpenStreetMap / Overpass  → Kulturorte (kein Key nötig)
- Ticketmaster API          → echte Events (kostenloser Key)
- Groq API                  → KI-Funktionen mit LLaMA 3 (kostenloser Key)

Keys eintragen in: kultur.env
    GROQ_API_KEY=gsk_...
    TICKETMASTER_API_KEY=...

Keys holen:
    Groq:         https://console.groq.com  → kostenlos registrieren → API Keys
    Ticketmaster: https://developer.ticketmaster.com → App registrieren → Consumer Key
"""

import os, json, math, requests
from datetime import datetime

# ─────────────────────────────────────────────
# ENV LADEN
# ─────────────────────────────────────────────
def lade_env(pfad="kultur.env"):
    if not os.path.exists(pfad):
        return
    with open(pfad) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

lade_env()

GROQ_API_KEY          = os.getenv("GROQ_API_KEY", "")
TICKETMASTER_API_KEY  = os.getenv("TICKETMASTER_API_KEY", "")

# ═════════════════════════════════════════════
# 1. OPENSTREETMAP – KULTURORTE (kein Key)
# ═════════════════════════════════════════════

OSM_TYPEN = {
    "Museum":     [('amenity','museum'), ('tourism','museum')],
    "Galerie":    [('amenity','gallery'), ('tourism','gallery')],
    "Theater":    [('amenity','theatre')],
    "Kino":       [('amenity','cinema')],
    "Club":       [('amenity','nightclub')],
    "Bibliothek": [('amenity','library')],
    "Kunstwerk":  [('tourism','artwork')],
    "Alle":       [('amenity','museum'),('amenity','gallery'),('amenity','theatre'),
                   ('amenity','cinema'),('amenity','nightclub'),('tourism','museum'),
                   ('tourism','gallery'),('tourism','artwork')],
}

EMOJI_MAP = {
    "museum":"🏛️","gallery":"🖼️","theatre":"🎭","cinema":"🎬",
    "nightclub":"🎵","library":"📚","artwork":"🎨",
}

def _geocode(stadt):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": stadt, "format": "json", "limit": 1},
            headers={"User-Agent": "kulturapp/2.0"},
            timeout=8
        )
        d = r.json()
        return float(d[0]["lat"]), float(d[0]["lon"]) if d else (52.52, 13.405)
    except:
        return 52.52, 13.405

def _entfernung(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return round(R * 2 * math.asin(math.sqrt(a)), 2)

def lade_kulturorte_osm(stadt="Berlin", kategorie="Alle", radius_km=5):
    """Lädt echte Kulturorte via OpenStreetMap. Komplett kostenlos."""
    lat, lon = _geocode(stadt)
    typen    = OSM_TYPEN.get(kategorie, OSM_TYPEN["Alle"])
    radius_m = radius_km * 1000

    teile = []
    for key, val in typen:
        teile.append(f'node["{key}"="{val}"](around:{radius_m},{lat},{lon});')
        teile.append(f'way["{key}"="{val}"](around:{radius_m},{lat},{lon});')

    query = f"[out:json][timeout:20];\n({''.join(teile)});\nout center 40;"

    try:
        r = requests.post("https://overpass-api.de/api/interpreter",
                          data={"data": query}, timeout=25)
        elems = r.json().get("elements", [])
    except:
        return []

    orte = []
    for el in elems:
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:de", "")
        if not name:
            continue
        el_lat = el.get("lat") or el.get("center", {}).get("lat", lat)
        el_lon = el.get("lon") or el.get("center", {}).get("lon", lon)
        amenity = tags.get("amenity") or tags.get("tourism", "ort")
        orte.append({
            "id":             f"osm_{el['id']}",
            "typ":            "Ort",
            "emoji":          EMOJI_MAP.get(amenity, "📍"),
            "titel":          name,
            "ort":            tags.get("addr:city", stadt),
            "adresse":        f"{tags.get('addr:street','')} {tags.get('addr:housenumber','')}".strip(),
            "oeffnung":       tags.get("opening_hours", "Keine Angabe"),
            "website":        tags.get("website") or tags.get("contact:website", ""),
            "beschreibung":   tags.get("description", f"{amenity.capitalize()} in {stadt}"),
            "kategorie":      amenity.capitalize(),
            "preis":          0,
            "barrierefreiheit": tags.get("wheelchair", "") in ["yes", "limited"],
            "lat":            el_lat, "lon": el_lon,
            "entfernung":     _entfernung(lat, lon, el_lat, el_lon),
            "quelle":         "OpenStreetMap",
            "altersgruppe":   "Alle",
            "zeitaufwand":    2,
            "datum":          "Täglich",
        })

    return sorted(orte, key=lambda x: x["entfernung"])


# ═════════════════════════════════════════════
# 2. TICKETMASTER API – ECHTE EVENTS (kostenlos)
# ═════════════════════════════════════════════

TM_KATEGORIEN = {
    "Musik":      "KZFzniwnSyZfZ7v7nJ",
    "Theater":    "KZFzniwnSyZfZ7v7na",
    "Kunst":      "KZFzniwnSyZfZ7v7nn",
    "Familie":    "KZFzniwnSyZfZ7v7n1",
    "Comedy":     "KZFzniwnSyZfZ7v7nE",
    "Alle":       None,
}

STADT_LAND = {
    "Berlin": "DE", "Hamburg": "DE", "München": "DE", "Köln": "DE",
    "Frankfurt": "DE", "Stuttgart": "DE", "Wien": "AT", "Zürich": "CH",
}

def lade_events_ticketmaster(stadt="Berlin", kategorie="Alle",
                              max_preis=200, radius_km=25, seite=0):
    """
    Lädt echte Events via Ticketmaster.
    Key: https://developer.ticketmaster.com → App erstellen → Consumer Key kopieren
    Kostenlos: 5.000 Anfragen/Tag
    """
    if not TICKETMASTER_API_KEY:
        return [], "⚠️ Kein Ticketmaster-Key. Trage TICKETMASTER_API_KEY in kultur.env ein."

    lat, lon  = _geocode(stadt)
    land      = STADT_LAND.get(stadt, "DE")
    kat_id    = TM_KATEGORIEN.get(kategorie)

    params = {
        "apikey":         TICKETMASTER_API_KEY,
        "latlong":        f"{lat},{lon}",
        "radius":         str(radius_km),
        "unit":           "km",
        "countryCode":    land,
        "size":           20,
        "page":           seite,
        "sort":           "date,asc",
        "locale":         "de-DE,en-US",
    }
    if kat_id:
        params["classificationId"] = kat_id

    try:
        r = requests.get(
            "https://app.ticketmaster.com/discovery/v2/events.json",
            params=params, timeout=12
        )
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.HTTPError as e:
        if r.status_code == 401:
            return [], "❌ Ungültiger Ticketmaster API-Key."
        return [], f"❌ Ticketmaster Fehler: {e}"
    except Exception as e:
        return [], f"❌ Verbindungsfehler: {e}"

    events_raw = data.get("_embedded", {}).get("events", [])
    events = []

    for ev in events_raw:
        # Preis
        preise = ev.get("priceRanges", [])
        preis  = preise[0].get("min", 0) if preise else 0
        if preis > max_preis:
            continue

        # Ort & Koordinaten
        venues = ev.get("_embedded", {}).get("venues", [{}])
        venue  = venues[0] if venues else {}
        v_city = venue.get("city", {}).get("name", stadt)
        v_addr = venue.get("address", {}).get("line1", "")
        v_name = venue.get("name", "")
        ev_lat = float(venue.get("location", {}).get("latitude",  lat) or lat)
        ev_lon = float(venue.get("location", {}).get("longitude", lon) or lon)

        # Datum & Zeit
        dates  = ev.get("dates", {})
        start  = dates.get("start", {})
        datum  = start.get("localDate", "")
        zeit   = start.get("localTime", "")[:5] if start.get("localTime") else ""

        # Kategorie
        klass  = ev.get("classifications", [{}])
        genre  = klass[0].get("genre", {}).get("name", "") if klass else ""
        segm   = klass[0].get("segment", {}).get("name", "Event") if klass else "Event"

        # Bild
        images = ev.get("images", [])
        bild   = next((i["url"] for i in images if i.get("ratio") == "16_9"), "🎭")

        events.append({
            "id":             ev["id"],
            "typ":            "Event",
            "emoji":          "🎭",
            "titel":          ev["name"],
            "beschreibung":   ev.get("info", ev.get("pleaseNote", f"{segm} in {v_city}"))[:200],
            "ort":            v_city,
            "venue":          v_name,
            "adresse":        v_addr,
            "lat":            ev_lat, "lon": ev_lon,
            "entfernung":     _entfernung(lat, lon, ev_lat, ev_lon),
            "datum":          datum,
            "oeffnung":       zeit,
            "preis":          round(preis, 2),
            "kategorie":      genre or segm,
            "url":            ev.get("url", ""),
            "bild":           bild,
            "barrierefreiheit": False,
            "zeitaufwand":    3,
            "altersgruppe":   "Alle",
            "quelle":         "Ticketmaster",
        })

    return events, None  # (events, fehler)


# ═════════════════════════════════════════════
# 3. GROQ API – KI MIT LLAMA 3 (kostenlos)
# ═════════════════════════════════════════════
# Key holen: https://console.groq.com
# → Registrieren → "Create API Key" → gsk_...
# Kostenlos: 14.400 Anfragen/Tag, sehr schnell

GROQ_URL    = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL  = "llama3-8b-8192"  # schnell & kostenlos

def _groq_request(prompt: str, max_tokens: int = 400, temperature: float = 0.7) -> str:
    """Basis-Funktion für alle Groq-Anfragen."""
    if not GROQ_API_KEY:
        return ""
    try:
        r = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type":  "application/json",
            },
            json={
                "model":       GROQ_MODEL,
                "messages":    [{"role": "user", "content": prompt}],
                "max_tokens":  max_tokens,
                "temperature": temperature,
            },
            timeout=20
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return ""


def ki_empfehlung(events: list, interessen: list, ort: str,
                  budget: int = 50, personen: int = 1) -> str:
    """Personalisierte Event-Empfehlung via Groq/LLaMA."""
    if not events:
        return "Keine Events zum Empfehlen verfügbar."

    ev_liste = "\n".join([
        f"- {e['titel']} ({e.get('kategorie','')}, {e.get('preis',0)}€, "
        f"{e.get('datum','')}, {e.get('entfernung',0)}km)"
        for e in events[:12]
    ])

    antwort = _groq_request(f"""Du bist ein freundlicher Kulturberater.
Interessen der Person: {', '.join(interessen) if interessen else 'Kunst, Musik, Kultur'}
Ort: {ort} | Budget: {budget}€ pro Person | Personen: {personen}

Verfügbare Events/Orte:
{ev_liste}

Empfehle 2-3 passende Events mit kurzer freundlicher Begründung.
Maximal 120 Wörter. Auf Deutsch. Keine langen Einleitungen.""",
        max_tokens=250)

    if not antwort:
        # Fallback ohne KI
        top = events[:2]
        return (f"✨ Empfehlung: **{top[0]['titel']}**"
                + (f" und **{top[1]['titel']}**" if len(top) > 1 else "") + ".")
    return antwort


def ki_smarte_suche(query: str, events: list) -> list:
    """Versteht natürliche Suchanfragen wie 'günstiges Abendprogramm'."""
    if not events:
        return []

    if not GROQ_API_KEY:
        # Fallback: einfache Textsuche
        q = query.lower()
        return [e for e in events
                if q in e["titel"].lower()
                or q in e.get("beschreibung", "").lower()
                or q in e.get("kategorie", "").lower()]

    ev_json = json.dumps([
        {"id": e["id"], "titel": e["titel"],
         "kategorie": e.get("kategorie", ""),
         "preis": e.get("preis", 0),
         "oeffnung": e.get("oeffnung", ""),
         "beschreibung": e.get("beschreibung", "")[:80]}
        for e in events
    ], ensure_ascii=False)

    antwort = _groq_request(
        f'Suchanfrage: "{query}"\n\nEvents:\n{ev_json}\n\n'
        f'Gib NUR eine JSON-Liste mit passenden IDs zurück. Format: ["id1","id2"]\n'
        f'Kein weiterer Text, nur die JSON-Liste.',
        max_tokens=150, temperature=0
    )

    try:
        ids = json.loads(antwort)
        result = [e for e in events if e["id"] in ids]
        return result if result else _fallback_suche(query, events)
    except:
        return _fallback_suche(query, events)


def ki_kunstwerk_beschreibung(titel: str, kategorie: str,
                               material: str = "", groesse: str = "") -> str:
    """Generiert professionelle Galerietexte für Marktplatz-Artikel."""
    antwort = _groq_request(
        f"""Schreibe einen professionellen Galerie-Text für dieses Kunstwerk:
Titel: {titel}
Kategorie: {kategorie}
Material: {material or 'nicht angegeben'}
Größe: {groesse or 'nicht angegeben'}

Stil: Poetisch aber sachlich. Wie in einer echten Galerie.
Länge: 2-3 Sätze, max. 70 Wörter. Auf Deutsch.""",
        max_tokens=150, temperature=0.8
    )
    return antwort or f"{titel} – ein einzigartiges Werk der Kategorie {kategorie}."


def ki_tagesplan(favoriten: list, startzeit: str = "10:00",
                  budget: int = 100, personen: int = 1) -> str:
    """Optimierter KI-Tagesplan aus Favoriten."""
    if not favoriten:
        return ""

    fav_liste = "\n".join([
        f"- {e['titel']}: ab {e.get('oeffnung','?')} Uhr, "
        f"ca. {e.get('zeitaufwand', 2)}h, {e.get('preis', 0)}€, "
        f"{e.get('entfernung', 0)}km entfernt"
        for e in favoriten
    ])

    antwort = _groq_request(
        f"""Erstelle einen optimierten Kultur-Tagesplan.
Startzeit: {startzeit} Uhr
Budget: {budget}€ für {personen} Person(en) (gesamt: {budget*personen}€)

Favorisierte Events:
{fav_liste}

Regeln:
1. Starte mit dem nächstgelegenen
2. Plane 20-30 Min Wegzeit zwischen Events
3. Füge eine Mittagspause ein
4. Bleibe im Budget

Erstelle einen konkreten Stundenplan. Freundlich und praktisch. Auf Deutsch.""",
        max_tokens=400, temperature=0.6
    )
    return antwort or _fallback_tagesplan(favoriten, startzeit)


# ─────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────
def _fallback_suche(query: str, events: list) -> list:
    q = query.lower()
    return [e for e in events
            if q in e["titel"].lower()
            or q in e.get("beschreibung", "").lower()
            or q in e.get("kategorie", "").lower()]


def _fallback_tagesplan(favoriten: list, startzeit: str) -> str:
    h = int(startzeit.split(":")[0])
    plan = []
    for i, e in enumerate(favoriten):
        end = h + e.get("zeitaufwand", 2)
        plan.append(f"🕐 {h:02d}:00 – {end:02d}:00 | {e['titel']} ({e.get('preis',0)}€)")
        h = end + 1
    return "\n".join(plan)


def api_status() -> dict:
    """Gibt den Status aller APIs zurück."""
    return {
        "OpenStreetMap": "✅ Aktiv (kein Key nötig)",
        "Ticketmaster":  "✅ Key vorhanden" if TICKETMASTER_API_KEY else "⚠️ Kein Key (demo.ticketmaster.com für kostenlosen Key)",
        "Groq KI":       "✅ Key vorhanden" if GROQ_API_KEY else "⚠️ Kein Key (console.groq.com für kostenlosen Key)",
    }
