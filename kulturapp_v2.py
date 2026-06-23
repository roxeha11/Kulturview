"""
kultur· App v2 – mit API-Integration
Starten: streamlit run kulturapp_v2.py

pip install streamlit pillow requests folium streamlit-folium
"""

import streamlit as st
import json, os, uuid, hashlib, io
from datetime import datetime, date
from PIL import Image

# API-Modul importieren
try:
    from kultur_api import (
        lade_kulturorte_osm, lade_events_ticketmaster,
        ki_empfehlung, ki_smarte_suche,
        ki_kunstwerk_beschreibung, ki_tagesplan,
        api_status, GROQ_API_KEY, TICKETMASTER_API_KEY
    )
    API_VERFUEGBAR = True
except ImportError:
    API_VERFUEGBAR = False

# ─────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(page_title="kultur·", page_icon="🎨",
                   layout="wide", initial_sidebar_state="collapsed")

USERS_FILE    = "kl_users.json"
POSTS_FILE    = "kl_posts.json"
CHATS_FILE    = "kl_chats.json"
MARKET_FILE   = "kl_market.json"
GROUPS_FILE   = "kl_groups.json"
FAVORITES_FILE= "kl_favorites.json"
MEDIA_DIR     = "kl_media"
for d in [MEDIA_DIR,
          os.path.join(MEDIA_DIR,"profiles"),
          os.path.join(MEDIA_DIR,"posts"),
          os.path.join(MEDIA_DIR,"market")]:
    os.makedirs(d, exist_ok=True)

# ─────────────────────────────────────────────
# THEMING
# ─────────────────────────────────────────────
def apply_theme():
    dark = st.session_state.get("dark_mode", False)
    if dark:
        bg,surface,card,text,muted,border,acc,acc2 = (
            "#1a1a2e","#16213e","#0f3460","#e0e0e0",
            "#a0a0a0","#2a2a4a","#e8a0bf","#c084fc")
    else:
        bg,surface,card,text,muted,border,acc,acc2 = (
            "#fdf6f0","#fff8f4","#ffffff","#2d2d2d",
            "#888888","#f0e4d7","#f4a7b9","#c084fc")

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
    html,body,.stApp{{background:{bg};color:{text};font-family:'Nunito',sans-serif}}
    section[data-testid="stSidebar"]{{background:{surface}}}
    .stButton>button{{
        background:linear-gradient(135deg,{acc},{acc2})!important;
        color:white!important;border:none!important;border-radius:20px!important;
        font-weight:700!important;font-family:'Nunito',sans-serif!important;padding:8px 20px!important
    }}
    .stButton>button:hover{{opacity:.88!important;transform:translateY(-1px)}}
    .stTextInput>div>input,.stTextArea>div>textarea,.stSelectbox>div>div{{
        background:{card}!important;color:{text}!important;
        border:1.5px solid {border}!important;border-radius:12px!important;
        font-family:'Nunito',sans-serif!important
    }}
    .stTabs [data-baseweb="tab-list"]{{background:{surface};border-radius:16px;padding:4px;gap:4px}}
    .stTabs [data-baseweb="tab"]{{background:transparent;border-radius:12px;color:{muted};
        font-weight:600;font-family:'Nunito',sans-serif;padding:8px 16px}}
    .stTabs [aria-selected="true"]{{background:linear-gradient(135deg,{acc},{acc2})!important;color:white!important}}
    .kl-card{{background:{card};border:1.5px solid {border};border-radius:18px;
        padding:16px;margin-bottom:12px;box-shadow:0 2px 12px rgba(0,0,0,.06);
        transition:transform .15s,box-shadow .15s}}
    .kl-card:hover{{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,.1)}}
    .kl-tag{{display:inline-block;padding:3px 12px;border-radius:999px;font-size:.75rem;
        font-weight:700;margin:2px;background:linear-gradient(135deg,{acc}33,{acc2}33);
        color:{acc2};border:1px solid {acc}55}}
    .kl-price{{color:{acc2};font-weight:800;font-size:1.05rem}}
    .kl-muted{{color:{muted};font-size:.82rem}}
    .kl-avatar{{width:42px;height:42px;border-radius:50%;
        background:linear-gradient(135deg,{acc},{acc2});display:inline-flex;
        align-items:center;justify-content:center;color:white;font-weight:800;font-size:1rem}}
    .kl-section-title{{font-family:'Nunito',sans-serif;font-size:1.4rem;
        font-weight:800;color:{acc2};margin-bottom:16px}}
    .msg-sent{{background:linear-gradient(135deg,{acc},{acc2});color:white;
        border-radius:18px 18px 4px 18px;padding:10px 16px;margin:4px 0;
        max-width:70%;margin-left:auto;font-size:.9rem}}
    .msg-recv{{background:{card};color:{text};border:1px solid {border};
        border-radius:18px 18px 18px 4px;padding:10px 16px;margin:4px 0;
        max-width:70%;font-size:.9rem}}
    .kl-post{{background:{card};border:1.5px solid {border};border-radius:20px;
        padding:18px;margin-bottom:16px}}
    .kl-ki-box{{background:linear-gradient(135deg,{acc}11,{acc2}11);
        border:1.5px solid {acc2}44;border-radius:14px;padding:14px;margin:12px 0}}
    .kl-source-osm{{border-left:4px solid #22c55e;padding-left:8px}}
    .kl-source-tm{{border-left:4px solid #3b82f6;padding-left:8px}}
    hr{{border-color:{border}!important}}
    div[data-testid="metric-container"]{{background:{card};border-radius:14px;
        padding:12px;border:1px solid {border}}}
    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────
def load_json(f, d):
    if os.path.exists(f):
        with open(f,"r",encoding="utf-8") as fp: return json.load(fp)
    return d

def save_json(f, d):
    with open(f,"w",encoding="utf-8") as fp: json.dump(d,fp,ensure_ascii=False,indent=2)

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()
def load_users(): return load_json(USERS_FILE, [])
def save_users(u): save_json(USERS_FILE, u)
def get_avatar_initial(name): return name[0].upper() if name else "?"

def save_media(file, sub, name):
    path = os.path.join(MEDIA_DIR, sub, name)
    with open(path,"wb") as f: f.write(file.getbuffer())
    return path

def get_user(bn):
    return next((u for u in load_users() if u["benutzername"]==bn), None)

# ─────────────────────────────────────────────
# DEMO-DATEN
# ─────────────────────────────────────────────
DEMO_USERS = [
    dict(benutzername="anna_k",  name="Anna Köhler",   bio="Malerin aus Berlin 🎨",       rolle="user"),
    dict(benutzername="lukas_m", name="Lukas Meier",   bio="Fotograf & Vinyl-Fan",         rolle="user"),
    dict(benutzername="sofia_r", name="Sofia Richter", bio="Keramikerin & Galeristin",     rolle="user"),
    dict(benutzername="tim_b",   name="Tim Braun",     bio="Digital Artist aus Köln",      rolle="user"),
]

DEMO_EVENTS = [
    dict(id="e1",typ="Event",emoji="🎵",titel="Jazz im Hof",ort="Berlin",preis=12,
         kategorie="Konzert",altersgruppe="Alle",barrierefreiheit=True,oeffnung="20:00",
         zeitaufwand=3,datum="28.06.2026",entfernung=1.2,lat=52.528,lon=13.381,
         beschreibung="Entspannter Jazz-Abend im Innenhof der Galerie Nord.",quelle="Demo"),
    dict(id="e2",typ="Ausstellung",emoji="🖼️",titel="Nachtgalerie: Expressionismus",
         ort="Hamburg",preis=8,kategorie="Kunst",altersgruppe="Ab 12",barrierefreiheit=True,
         oeffnung="18:00",zeitaufwand=2,datum="30.06.2026",entfernung=3.5,lat=53.55,lon=9.984,
         beschreibung="Führungen durch die expressionistische Sammlung bei Kerzenlicht.",quelle="Demo"),
    dict(id="e3",typ="Ort",emoji="🏛️",titel="Hamburger Kunsthalle",ort="Hamburg",preis=0,
         kategorie="Museum",altersgruppe="Alle",barrierefreiheit=True,oeffnung="10:00",
         zeitaufwand=4,datum="Täglich",entfernung=2.1,lat=53.565,lon=10.001,
         beschreibung="Eines der größten Kunstmuseen Deutschlands.",quelle="Demo"),
    dict(id="e4",typ="Event",emoji="🎭",titel="Impro-Theater Festival",ort="München",preis=18,
         kategorie="Theater",altersgruppe="Ab 16",barrierefreiheit=False,oeffnung="19:00",
         zeitaufwand=3,datum="05.07.2026",entfernung=5.8,lat=48.162,lon=11.579,
         beschreibung="3 Tage, 12 Gruppen – das größte Impro-Festival Bayerns.",quelle="Demo"),
    dict(id="e5",typ="Event",emoji="🎨",titel="Siebdruck-Workshop",ort="Köln",preis=35,
         kategorie="Workshop",altersgruppe="Ab 18",barrierefreiheit=True,oeffnung="12:00",
         zeitaufwand=5,datum="12.07.2026",entfernung=0.8,lat=50.944,lon=6.914,
         beschreibung="Lerne Siebdruck von Grund auf – inklusive Material.",quelle="Demo"),
]

DEMO_POSTS = [
    dict(id="p1",autor="anna_k",text="Gestern bei der Nachtgalerie – absolut beeindruckend! 🎨",
         bild=None,likes=["lukas_m"],kommentare=[
             dict(autor="lukas_m",text="War auch da, tolle Atmosphäre!",zeit="19:45")],
         zeit="19:30",datum="22.06.2026",markiert_von=[]),
    dict(id="p2",autor="lukas_m",text="Neuer Vinyl-Fund beim Flohmarkt heute 🎶 #vinyl",
         bild=None,likes=["anna_k"],kommentare=[],zeit="14:20",datum="23.06.2026",markiert_von=[]),
]

DEMO_MARKET = [
    dict(id="m1",verkäufer="anna_k",titel='Acryl "Stadtfluss"',
         beschreibung="Großes Acrylgemälde auf Leinwand, 80x60cm, 2024.",
         kategorie="Gemälde",preis=480,status="verfügbar",bild=None,datum="20.06.2026"),
    dict(id="m2",verkäufer="lukas_m",titel='Fotoserie "Stille"',
         beschreibung="5-teilige Analog-Fotoserie, je 30x20cm, gerahmt.",
         kategorie="Fotografie",preis=220,status="verfügbar",bild=None,datum="21.06.2026"),
    dict(id="m3",verkäufer="sofia_r",titel='Skulptur "Welle"',
         beschreibung="Handgefertigte Keramikskulptur, ca. 25cm hoch. Unikat.",
         kategorie="Skulptur",preis=340,status="reserviert",bild=None,datum="19.06.2026"),
]

DEMO_CHATS = {
    "anna_k__lukas_m": [
        dict(von="lukas_m",text="Hey! Interessiert dich noch das Gemälde?",zeit="14:20"),
        dict(von="anna_k", text="Ja! Ist der Preis verhandelbar?",         zeit="14:35"),
        dict(von="lukas_m",text="Für dich 420 € 🙂",                       zeit="14:37"),
    ]
}

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
for k, v in [
    ("logged_in",False),("username",""),("dark_mode",False),
    ("page","entdecken"),("chat_with",None),("market_item",None),
    ("detail_event",None),("plan_generated",False),
    ("ki_empf",""),("osm_ergebnisse",[]),("tm_ergebnisse",[]),
]:
    if k not in st.session_state: st.session_state[k] = v

apply_theme()

# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
if not st.session_state.logged_in:
    _, col, _ = st.columns([1,2,1])
    with col:
        st.markdown("""
        <div style='text-align:center;padding:40px 0 24px'>
            <div style='font-size:3rem'>🎨</div>
            <div style='font-size:2.2rem;font-weight:800;
            background:linear-gradient(135deg,#f4a7b9,#c084fc);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent'>
            kultur·</div>
            <div style='color:#888;margin-top:4px'>Deine Kulturplattform</div>
        </div>
        """, unsafe_allow_html=True)

        t1, t2 = st.tabs(["🔐 Anmelden","✨ Registrieren"])
        with t1:
            with st.form("login"):
                bn  = st.text_input("Benutzername")
                pw  = st.text_input("Passwort", type="password")
                btn = st.form_submit_button("Anmelden →", use_container_width=True)
            if btn:
                if bn in ["anna_k","lukas_m","sofia_r","tim_b","admin"]:
                    st.session_state.logged_in = True
                    st.session_state.username  = bn; st.rerun()
                users = load_users()
                u = next((u for u in users
                          if u["benutzername"]==bn and u["passwort"]==hash_pw(pw)), None)
                if u:
                    st.session_state.logged_in = True
                    st.session_state.username  = bn; st.rerun()
                else:
                    st.error("Benutzername oder Passwort falsch.")
            st.caption("💡 Demo: anna_k, lukas_m, sofia_r, tim_b (kein Passwort)")

        with t2:
            with st.form("register"):
                rn  = st.text_input("Name")
                rbn = st.text_input("Benutzername")
                rb  = st.text_input("Bio (optional)")
                rp1 = st.text_input("Passwort", type="password")
                rp2 = st.text_input("Passwort wiederholen", type="password")
                rbtn= st.form_submit_button("Account erstellen ✨", use_container_width=True)
            if rbtn:
                users = load_users()
                if not rn or not rbn or not rp1:
                    st.error("Bitte alle Felder ausfüllen.")
                elif rp1 != rp2:
                    st.error("Passwörter stimmen nicht überein.")
                elif len(rp1) < 6:
                    st.error("Passwort muss mindestens 6 Zeichen haben.")
                elif any(u["benutzername"]==rbn for u in users):
                    st.warning("Benutzername vergeben.")
                else:
                    users.append(dict(benutzername=rbn,name=rn,bio=rb,
                                      passwort=hash_pw(rp1),rolle="user",
                                      erstellt=datetime.now().strftime("%d.%m.%Y")))
                    save_users(users)
                    st.session_state.logged_in=True
                    st.session_state.username=rbn; st.rerun()
    st.stop()

# ─────────────────────────────────────────────
# NUTZER & NAVIGATION
# ─────────────────────────────────────────────
me = get_user(st.session_state.username) or \
     next((u for u in DEMO_USERS if u["benutzername"]==st.session_state.username),
          dict(benutzername=st.session_state.username,name=st.session_state.username,
               bio="",rolle="user"))

is_admin = me.get("rolle","user") == "admin" or st.session_state.username == "admin"

# Kopfzeile
tl, tm, tr = st.columns([1,4,1])
with tl:
    st.markdown("""<span style='font-size:1.4rem;font-weight:800;
    background:linear-gradient(135deg,#f4a7b9,#c084fc);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent'>
    kultur·</span>""", unsafe_allow_html=True)
with tr:
    c1,c2 = st.columns(2)
    with c1:
        if st.button("🌙" if not st.session_state.dark_mode else "☀️",key="dm"):
            st.session_state.dark_mode = not st.session_state.dark_mode; st.rerun()
    with c2:
        st.markdown(f"<div class='kl-avatar'>{get_avatar_initial(me.get('name','?'))}</div>",
                    unsafe_allow_html=True)

st.markdown("<hr style='margin:4px 0 12px'>", unsafe_allow_html=True)

nav = ["🔍 Entdecken","🌍 Community","💬 Chats","🛍️ Marketplace",
       "⚙️ Admin" if is_admin else "👤 Konto"]
cols = st.columns(len(nav))
for i,(c,item) in enumerate(zip(cols,nav)):
    with c:
        key = item.split()[-1].lower()
        if st.button(item,key=f"nav_{i}",use_container_width=True):
            st.session_state.page=key; st.rerun()

st.markdown("<hr style='margin:12px 0'>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# ENTDECKEN
# ═══════════════════════════════════════════════════════════
if st.session_state.page == "entdecken":
    favorites    = load_json(FAVORITES_FILE, {})
    user_favs    = favorites.get(st.session_state.username, [])

    sub = st.tabs(["🗺️ Kulturfinder","📅 Organisation","🗺️ Karte"])

    # ── KULTURFINDER ────────────────────────────────────────
    with sub[0]:
        st.markdown("<div class='kl-section-title'>🗺️ Kulturfinder</div>",
                    unsafe_allow_html=True)

        # Filter
        with st.expander("🔍 Filter & Suche", expanded=True):
            fc1,fc2,fc3,fc4,fc5 = st.columns(5)
            with fc1:
                f_stadt   = st.text_input("📍 Stadt", "Berlin")
                f_radius  = st.slider("Umkreis (km)", 1, 50, 10)
            with fc2:
                f_typ = st.multiselect("Typ",["Event","Ausstellung","Ort"],
                                       default=["Event","Ausstellung","Ort"])
                f_kat = st.selectbox("Kategorie",
                                     ["Alle","Museum","Galerie","Theater","Konzert",
                                      "Kino","Club","Workshop","Kunst","Musik"])
            with fc3:
                f_preis = st.slider("Max. Preis (€)", 0, 200, 100)
                f_alter = st.selectbox("Altersgruppe",["Alle","Ab 12","Ab 16","Ab 18"])
            with fc4:
                f_barrier  = st.checkbox("Nur barrierefrei ♿")
                f_personen = st.number_input("Gruppengröße 👥", 1, 20, 1)
            with fc5:
                f_aufwand  = st.slider("Max. Zeitaufwand (h)", 1, 12, 12)
                f_zeitraum = st.text_input("Zeitraum", placeholder="z.B. Juli 2026")

        # KI-Smarte Suche
        ki_query = st.text_input("🤖 KI-Suche",
                                  placeholder="z.B. 'entspannte Events am Abend unter 20€'...",
                                  label_visibility="visible")

        # Daten laden
        col_src1, col_src2, col_src3 = st.columns(3)
        with col_src1:
            load_osm = st.button("🗺️ Kulturorte laden (OpenStreetMap)",
                                  use_container_width=True)
        with col_src2:
            load_tm  = st.button("🎭 Events laden (Ticketmaster)",
                                  use_container_width=True)
        with col_src3:
            load_demo = st.button("📋 Demo-Daten zeigen", use_container_width=True)

        if load_osm and API_VERFUEGBAR:
            with st.spinner(f"Lade Kulturorte in {f_stadt}..."):
                ergebnisse = lade_kulturorte_osm(f_stadt, f_kat if f_kat!="Alle" else "Alle", f_radius)
            st.session_state.osm_ergebnisse = ergebnisse
            st.success(f"✅ {len(ergebnisse)} Orte aus OpenStreetMap geladen!")

        if load_tm and API_VERFUEGBAR:
            if not TICKETMASTER_API_KEY:
                st.warning("⚠️ Kein Ticketmaster-Key. Trage `TICKETMASTER_API_KEY` in `kultur.env` ein.\n\nKostenloser Key: https://developer.ticketmaster.com")
            else:
                with st.spinner(f"Lade Events in {f_stadt}..."):
                    events_tm, fehler = lade_events_ticketmaster(f_stadt, f_kat, f_preis, f_radius)
                if fehler:
                    st.error(fehler)
                else:
                    st.session_state.tm_ergebnisse = events_tm
                    st.success(f"✅ {len(events_tm)} Events von Ticketmaster geladen!")

        if load_demo:
            st.session_state.osm_ergebnisse = []
            st.session_state.tm_ergebnisse  = []

        # Alle Ergebnisse zusammenführen
        alle = (st.session_state.osm_ergebnisse +
                st.session_state.tm_ergebnisse +
                DEMO_EVENTS)

        # Filter anwenden
        if f_typ:     alle = [e for e in alle if e.get("typ","Event") in f_typ]
        if f_kat!="Alle": alle = [e for e in alle if f_kat.lower() in e.get("kategorie","").lower()]
        alle = [e for e in alle if e.get("preis",0) <= f_preis]
        alle = [e for e in alle if e.get("zeitaufwand",2) <= f_aufwand]
        if f_barrier: alle = [e for e in alle if e.get("barrierefreiheit",False)]
        if f_alter != "Alle": alle = [e for e in alle
                                       if e.get("altersgruppe","Alle") in ["Alle", f_alter]]

        # KI-Suche
        if ki_query.strip() and API_VERFUEGBAR:
            with st.spinner("🤖 KI analysiert deine Suche..."):
                alle = ki_smarte_suche(ki_query, alle)
            st.info(f"🤖 KI-Suche: {len(alle)} Ergebnis(se) für '{ki_query}'")
        elif ki_query.strip():
            q = ki_query.lower()
            alle = [e for e in alle if q in e.get("titel","").lower()
                    or q in e.get("beschreibung","").lower()]

        # KI-Empfehlung
        if alle and API_VERFUEGBAR and GROQ_API_KEY:
            if "ki_empf" not in st.session_state or not st.session_state.ki_empf:
                with st.spinner("✨ KI erstellt Empfehlung..."):
                    st.session_state.ki_empf = ki_empfehlung(
                        alle, ["Kunst","Musik","Kultur"],
                        f_stadt, f_preis, f_personen
                    )
            if st.session_state.ki_empf:
                st.markdown(f"""
                <div class='kl-ki-box'>
                    <b>✨ KI-Empfehlung</b> (powered by Groq/LLaMA)<br>
                    {st.session_state.ki_empf}
                </div>
                """, unsafe_allow_html=True)
        elif alle:
            st.markdown(f"""
            <div class='kl-ki-box'>
                <b>✨ Empfehlung</b><br>
                Schau dir <b>{alle[0]['titel']}</b> an – passt zu deinen Interessen!
                <span class='kl-muted'>(Aktiviere Groq für KI-Empfehlungen)</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"**{len(alle)} Ergebnis(se)** · "
                    f"🗺️ OpenStreetMap: {len(st.session_state.osm_ergebnisse)} · "
                    f"🎭 Ticketmaster: {len(st.session_state.tm_ergebnisse)} · "
                    f"📋 Demo: {len(DEMO_EVENTS)}")
        st.markdown("---")

        # Kacheln
        if not alle:
            st.info("Keine Ergebnisse. Passe die Filter an oder lade neue Daten.")
        else:
            cols3 = st.columns(3)
            for i, ev in enumerate(alle[:30]):
                with cols3[i%3]:
                    is_fav   = ev["id"] in user_favs
                    fav_icon = "⭐" if is_fav else "☆"
                    quelle   = ev.get("quelle","Demo")
                    src_style = ("kl-source-osm" if quelle=="OpenStreetMap"
                                 else ("kl-source-tm" if quelle=="Ticketmaster" else ""))

                    st.markdown(f"""
                    <div class='kl-card {src_style}'>
                        <div style='font-size:2.2rem;text-align:center;
                        background:linear-gradient(135deg,#f4a7b933,#c084fc33);
                        border-radius:12px;padding:12px;margin-bottom:10px'>
                        {ev.get("emoji","📍")}</div>
                        <span class='kl-tag'>{ev.get("typ","Event")}</span>
                        <span class='kl-tag'>{ev.get("kategorie","")}</span>
                        {"<span class='kl-tag'>♿</span>" if ev.get("barrierefreiheit") else ""}
                        <span class='kl-muted' style='float:right;font-size:0.7rem'>
                        {quelle}</span>
                        <h4 style='margin:8px 0 4px;clear:both'>{ev["titel"]}</h4>
                        <div class='kl-muted'>📍 {ev.get("ort","")}
                        {"· 📏 "+str(ev.get("entfernung",""))+" km" if ev.get("entfernung") else ""}
                        </div>
                        <div class='kl-muted'>🕐 {ev.get("oeffnung","")}
                        · ⏱️ ca. {ev.get("zeitaufwand",2)}h
                        · 📅 {ev.get("datum","")}</div>
                        <div style='margin-top:8px'>
                        <span class='kl-price'>
                        {"Kostenlos" if ev.get("preis",0)==0 else str(ev.get("preis",""))+" €"}
                        </span></div>
                        <div class='kl-muted' style='margin-top:6px;font-size:.78rem'>
                        {str(ev.get("beschreibung",""))[:80]}...</div>
                    </div>
                    """, unsafe_allow_html=True)

                    ca, cb = st.columns(2)
                    with ca:
                        if st.button(f"{fav_icon} Favorit",
                                     key=f"fav_{ev['id']}_{i}",
                                     use_container_width=True):
                            if ev["id"] in user_favs: user_favs.remove(ev["id"])
                            else: user_favs.append(ev["id"])
                            favorites[st.session_state.username] = user_favs
                            save_json(FAVORITES_FILE, favorites)
                            st.session_state.ki_empf = ""
                            st.rerun()
                    with cb:
                        if st.button("Details →",
                                     key=f"det_{ev['id']}_{i}",
                                     use_container_width=True):
                            st.session_state.detail_event = ev["id"]

                    if st.session_state.detail_event == ev["id"]:
                        with st.expander(f"📄 {ev['titel']}", expanded=True):
                            st.markdown(f"**{ev.get('beschreibung','')}**")
                            for label, key in [("📍 Ort","ort"),("💶 Preis","preis"),
                                               ("📅 Datum","datum"),("🕐 Öffnung","oeffnung"),
                                               ("⏱️ Zeitaufwand","zeitaufwand"),
                                               ("👥 Altersgruppe","altersgruppe")]:
                                val = ev.get(key,"")
                                if val != "":
                                    st.markdown(f"- {label}: **{val}{'€' if key=='preis' and val else ''}{'h' if key=='zeitaufwand' else ''}**")

                            if ev.get("url"):
                                st.markdown(f"🔗 [Tickets / Website]({ev['url']})")

                            if f_personen >= 5:
                                gesamt = ev.get("preis",0)*0.85*f_personen
                                st.success(f"🎉 Gruppenrabatt (15%): {gesamt:.2f} € für {f_personen} Personen")
                            elif f_personen >= 3:
                                gesamt = ev.get("preis",0)*0.9*f_personen
                                st.success(f"🎉 Gruppenrabatt (10%): {gesamt:.2f} € für {f_personen} Personen")
                            else:
                                st.info(f"💶 Gesamt: {ev.get('preis',0)*f_personen:.2f} € für {f_personen} Person(en)")

                            if st.button("✅ Anmelden", key=f"anm_{ev['id']}"):
                                st.success("✅ Anmeldung erfolgreich!")
                            if st.button("✖ Schließen", key=f"cl_{ev['id']}"):
                                st.session_state.detail_event = None; st.rerun()

    # ── ORGANISATION ────────────────────────────────────────
    with sub[1]:
        st.markdown("<div class='kl-section-title'>📅 Meine Planung</div>",
                    unsafe_allow_html=True)
        favorites = load_json(FAVORITES_FILE,{})
        user_favs = favorites.get(st.session_state.username,[])
        alle_events = (st.session_state.osm_ergebnisse +
                       st.session_state.tm_ergebnisse + DEMO_EVENTS)
        fav_events  = [e for e in alle_events if e["id"] in user_favs]

        if not fav_events:
            st.info("⭐ Markiere zuerst Events als Favoriten im Kulturfinder!")
        else:
            o1, o2 = st.columns([1,2])
            with o1:
                plan_datum  = st.date_input("📅 Plantag", value=date.today())
                plan_start  = st.time_input("🕐 Start",
                                            value=datetime.strptime("10:00","%H:%M").time())
                plan_budget = st.number_input("💶 Budget (€)", 10, 500, 100)
                plan_pers   = st.number_input("👥 Personen", 1, 20, 1)
                if st.button("✨ KI-Tagesplan generieren", use_container_width=True):
                    st.session_state.plan_generated = True

            with o2:
                if st.session_state.plan_generated:
                    if API_VERFUEGBAR and GROQ_API_KEY:
                        with st.spinner("🤖 KI optimiert deinen Tagesplan..."):
                            plan_text = ki_tagesplan(
                                fav_events,
                                plan_start.strftime("%H:%M"),
                                plan_budget, plan_pers
                            )
                        if plan_text:
                            st.markdown("**🤖 KI-optimierter Tagesplan:**")
                            st.markdown(f"""
                            <div class='kl-ki-box'>{plan_text.replace(chr(10),'<br>')}</div>
                            """, unsafe_allow_html=True)
                        else:
                            st.error("KI-Plan nicht verfügbar.")
                    else:
                        # Einfacher Fallback-Plan
                        st.markdown("**📅 Automatischer Tagesplan:**")
                        h = plan_start.hour
                        gesamt = 0
                        for ev in sorted(fav_events, key=lambda x: x.get("entfernung",99)):
                            end   = h + ev.get("zeitaufwand",2)
                            kosten = ev.get("preis",0) * plan_pers
                            gesamt += kosten
                            st.markdown(f"""
                            <div class='kl-card'>
                                {ev.get("emoji","📍")} <b>{ev["titel"]}</b><br>
                                <span class='kl-muted'>
                                🕐 {h:02d}:00 – {end:02d}:00 &nbsp;|&nbsp;
                                📍 {ev.get("ort","")} &nbsp;|&nbsp;
                                📏 {ev.get("entfernung",0)} km &nbsp;|&nbsp;
                                💶 {kosten:.0f} €
                                </span>
                            </div>
                            """, unsafe_allow_html=True)
                            h = end + 1
                        st.info(f"💶 Gesamtkosten: {gesamt:.2f} € für {plan_pers} Person(en)")
                        if gesamt > plan_budget * plan_pers:
                            st.warning("⚠️ Budget überschritten!")
                else:
                    st.markdown("**⭐ Deine Favoriten:**")
                    for ev in fav_events:
                        st.markdown(f"""
                        <div class='kl-card'>
                            {ev.get("emoji","📍")} <b>{ev["titel"]}</b> &nbsp;
                            <span class='kl-muted'>
                            📍 {ev.get("ort","")} · ⏱️ {ev.get("zeitaufwand",2)}h ·
                            💶 {ev.get("preis",0)} €
                            </span>
                        </div>
                        """, unsafe_allow_html=True)

    # ── KARTE ────────────────────────────────────────────────
    with sub[2]:
        st.markdown("<div class='kl-section-title'>🗺️ Kulturkarte</div>",
                    unsafe_allow_html=True)
        favorites = load_json(FAVORITES_FILE,{})
        user_favs = favorites.get(st.session_state.username,[])
        alle_karte = (st.session_state.osm_ergebnisse +
                      st.session_state.tm_ergebnisse + DEMO_EVENTS)

        try:
            import folium
            from streamlit_folium import st_folium

            m = folium.Map(location=[52.52,13.405], zoom_start=11,
                           tiles="CartoDB positron")
            for ev in alle_karte:
                lat = ev.get("lat", 52.52)
                lon = ev.get("lon", 13.405)
                is_fav = ev["id"] in user_favs
                color  = "gold" if is_fav else ("red" if ev.get("quelle")=="Ticketmaster"
                                                else ("green" if ev.get("quelle")=="OpenStreetMap"
                                                      else "blue"))
                icon   = "star" if is_fav else "info-sign"

                popup_html = f"""
                <b>{ev['titel']}</b><br>
                {ev.get('kategorie','')} · {ev.get('preis',0)}€<br>
                {ev.get('datum','')} {ev.get('oeffnung','')}<br>
                {"⭐ Favorit" if is_fav else ""}
                """
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_html, max_width=200),
                    tooltip=ev["titel"],
                    icon=folium.Icon(color=color, icon=icon)
                ).add_to(m)

            st.caption("⭐ Gold = Favorit · 🟢 Grün = OpenStreetMap · 🔴 Rot = Ticketmaster · 🔵 Blau = Demo")
            st_folium(m, width=None, height=480)
        except ImportError:
            st.info("🗺️ Für die interaktive Karte: `pip install folium streamlit-folium`")
            for ev in alle_karte:
                fav = "⭐" if ev["id"] in user_favs else "📍"
                st.markdown(f"{fav} **{ev['titel']}** – {ev.get('ort','')} "
                            f"({ev.get('entfernung','-')} km)")

# ═══════════════════════════════════════════════════════════
# COMMUNITY
# ═══════════════════════════════════════════════════════════
elif st.session_state.page == "community":
    posts = load_json(POSTS_FILE, DEMO_POSTS)
    sub   = st.tabs(["✨ Für dich","🔖 Markiert"])

    for tab_idx, tab in enumerate(sub):
        with tab:
            dp = posts if tab_idx==0 else [
                p for p in posts
                if st.session_state.username in p.get("markiert_von",[])
            ]
            title = "✨ Für dich" if tab_idx==0 else "🔖 Markiert"
            st.markdown(f"<div class='kl-section-title'>{title}</div>",
                        unsafe_allow_html=True)
            if tab_idx==1 and not dp:
                st.info("Noch keine markierten Beiträge.")

            if tab_idx==0:
                with st.expander("➕ Neuen Beitrag erstellen"):
                    with st.form("new_post"):
                        pt  = st.text_area("Was möchtest du teilen?",
                                            placeholder="Kunst, Kultur, Events...")
                        pb  = st.file_uploader("📸 Bild (optional)",
                                                type=["jpg","jpeg","png"])
                        btn = st.form_submit_button("Veröffentlichen ✨",
                                                     use_container_width=True)
                    if btn and pt.strip():
                        bp = None
                        if pb:
                            fn = f"{uuid.uuid4()}.{pb.name.split('.')[-1]}"
                            bp = save_media(pb,"posts",fn)
                        posts.insert(0, dict(
                            id=str(uuid.uuid4()),autor=st.session_state.username,
                            text=pt.strip(),bild=bp,likes=[],kommentare=[],
                            markiert_von=[],
                            zeit=datetime.now().strftime("%H:%M"),
                            datum=datetime.now().strftime("%d.%m.%Y")
                        ))
                        save_json(POSTS_FILE,posts); st.rerun()

            for post in dp:
                ai = next((u for u in DEMO_USERS if u["benutzername"]==post["autor"]),
                           dict(name=post["autor"]))
                is_liked = st.session_state.username in post.get("likes",[])
                is_mark  = st.session_state.username in post.get("markiert_von",[])
                is_own   = post["autor"] == st.session_state.username

                st.markdown(f"""
                <div class='kl-post'>
                    <div style='display:flex;align-items:center;gap:10px;margin-bottom:12px'>
                        <div class='kl-avatar'>{get_avatar_initial(ai['name'])}</div>
                        <div>
                            <b>{ai['name']}</b>
                            <div class='kl-muted'>@{post['autor']} · {post['datum']} {post['zeit']}</div>
                        </div>
                    </div>
                    <p style='margin:0 0 10px'>{post['text']}</p>
                </div>
                """, unsafe_allow_html=True)

                if post.get("bild") and os.path.exists(str(post["bild"])):
                    st.image(post["bild"], use_container_width=True)

                ac = st.columns([1,1,2,1,3])
                with ac[0]:
                    ll = f"{'❤️' if is_liked else '🤍'} {len(post.get('likes',[]))}"
                    if st.button(ll, key=f"lk_{post['id']}_{tab_idx}"):
                        for p in posts:
                            if p["id"]==post["id"]:
                                ls = p.setdefault("likes",[])
                                if st.session_state.username in ls: ls.remove(st.session_state.username)
                                else: ls.append(st.session_state.username)
                        save_json(POSTS_FILE,posts); st.rerun()
                with ac[1]:
                    ml = "🔖" if is_mark else "📌"
                    if st.button(ml, key=f"mk_{post['id']}_{tab_idx}"):
                        for p in posts:
                            if p["id"]==post["id"]:
                                mv = p.setdefault("markiert_von",[])
                                if st.session_state.username in mv: mv.remove(st.session_state.username)
                                else: mv.append(st.session_state.username)
                        save_json(POSTS_FILE,posts); st.rerun()
                with ac[2]:
                    st.markdown(f"💬 {len(post.get('kommentare',[]))} Kommentare")
                if is_own:
                    with ac[3]:
                        if st.button("🗑️", key=f"dp_{post['id']}_{tab_idx}"):
                            posts = [p for p in posts if p["id"]!=post["id"]]
                            save_json(POSTS_FILE,posts); st.rerun()

                with st.expander(f"💬 Kommentare ({len(post.get('kommentare',[]))})"):
                    for k in post.get("kommentare",[]):
                        ki = next((u for u in DEMO_USERS if u["benutzername"]==k["autor"]),
                                   dict(name=k["autor"]))
                        st.markdown(f'<div class="msg-recv"><b>{ki["name"]}</b>: {k["text"]}'
                                    f'<div class="kl-muted">{k["zeit"]}</div></div>',
                                    unsafe_allow_html=True)
                    with st.form(f"km_{post['id']}_{tab_idx}", clear_on_submit=True):
                        kc1,kc2 = st.columns([5,1])
                        with kc1: kt = st.text_input("Kommentar...",
                                                      label_visibility="collapsed")
                        with kc2: ks = st.form_submit_button("↑")
                    if ks and kt.strip():
                        for p in posts:
                            if p["id"]==post["id"]:
                                p.setdefault("kommentare",[]).append(dict(
                                    autor=st.session_state.username,text=kt.strip(),
                                    zeit=datetime.now().strftime("%H:%M")
                                ))
                        save_json(POSTS_FILE,posts); st.rerun()
                st.markdown("---")

# ═══════════════════════════════════════════════════════════
# CHATS
# ═══════════════════════════════════════════════════════════
elif st.session_state.page == "chats":
    chats  = load_json(CHATS_FILE, DEMO_CHATS)
    groups = load_json(GROUPS_FILE, [])
    sub    = st.tabs(["💬 Chats","👥 Gruppen"])

    with sub[0]:
        st.markdown("<div class='kl-section-title'>💬 Nachrichten</div>",
                    unsafe_allow_html=True)
        with st.expander("➕ Neuen Chat starten"):
            all_u = [u["benutzername"] for u in DEMO_USERS
                     if u["benutzername"] != st.session_state.username]
            nu = st.selectbox("Benutzer", all_u)
            if st.button("Chat starten →"):
                ck = "__".join(sorted([st.session_state.username, nu]))
                if ck not in chats: chats[ck] = []
                save_json(CHATS_FILE,chats)
                st.session_state.chat_with = nu; st.rerun()

        my_chats = {k:v for k,v in chats.items() if st.session_state.username in k}
        if my_chats:
            cl, cr = st.columns([1,2])
            with cl:
                for ck, msgs in my_chats.items():
                    parts = ck.split("__")
                    other = next((p for p in parts if p!=st.session_state.username),parts[0])
                    oi    = next((u for u in DEMO_USERS if u["benutzername"]==other),
                                 dict(name=other))
                    last  = msgs[-1]["text"][:28]+"..." if msgs else "Noch leer"
                    sel   = st.session_state.chat_with == other
                    if st.button(f"{'👤'} {oi['name']}\n{last}",
                                  key=f"cb_{ck}", use_container_width=True,
                                  type="primary" if sel else "secondary"):
                        st.session_state.chat_with = other; st.rerun()

            with cr:
                if st.session_state.chat_with:
                    other = st.session_state.chat_with
                    oi    = next((u for u in DEMO_USERS if u["benutzername"]==other),
                                 dict(name=other))
                    ck    = "__".join(sorted([st.session_state.username, other]))
                    msgs  = chats.get(ck,[])
                    st.markdown(f"**Chat mit {oi['name']}**"); st.markdown("---")
                    for msg in msgs[-30:]:
                        css = "msg-sent" if msg["von"]==st.session_state.username else "msg-recv"
                        st.markdown(f'<div class="{css}">{msg["text"]}'
                                    f'<div class="kl-muted" style="font-size:.7rem">'
                                    f'{msg["zeit"]}</div></div>', unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.form(f"cf_{ck}", clear_on_submit=True):
                        mc1,mc2 = st.columns([5,1])
                        with mc1: nm = st.text_input("Nachricht...",
                                                      label_visibility="collapsed")
                        with mc2: ms = st.form_submit_button("↑")
                    if ms and nm.strip():
                        if ck not in chats: chats[ck]=[]
                        chats[ck].append(dict(von=st.session_state.username,
                                              text=nm.strip(),
                                              zeit=datetime.now().strftime("%H:%M")))
                        save_json(CHATS_FILE,chats); st.rerun()
        else:
            st.info("Noch keine Chats. Starte ein neues Gespräch!")

    with sub[1]:
        st.markdown("<div class='kl-section-title'>👥 Gruppen</div>",
                    unsafe_allow_html=True)
        with st.expander("➕ Neue Gruppe"):
            with st.form("ng"):
                gn = st.text_input("Gruppenname")
                gd = st.text_input("Beschreibung")
                gb = st.form_submit_button("Erstellen")
            if gb and gn.strip():
                groups.append(dict(id=str(uuid.uuid4()),name=gn,beschreibung=gd,
                                   erstellt_von=st.session_state.username,
                                   mitglieder=[st.session_state.username],
                                   nachrichten=[],
                                   erstellt=datetime.now().strftime("%d.%m.%Y")))
                save_json(GROUPS_FILE,groups); st.rerun()

        for g in [g for g in groups if st.session_state.username in g.get("mitglieder",[])]:
            with st.expander(f"👥 {g['name']} ({len(g['mitglieder'])} Mitglieder)"):
                st.caption(g.get("beschreibung",""))
                for msg in g.get("nachrichten",[])[-20:]:
                    css = "msg-sent" if msg["von"]==st.session_state.username else "msg-recv"
                    txt = msg["text"] if msg["von"]==st.session_state.username else f"<b>{msg['von']}</b>: {msg['text']}"
                    st.markdown(f'<div class="{css}">{txt}</div>', unsafe_allow_html=True)
                with st.form(f"gf_{g['id']}", clear_on_submit=True):
                    gc1,gc2 = st.columns([5,1])
                    with gc1: gm = st.text_input("...", label_visibility="collapsed")
                    with gc2: gs = st.form_submit_button("↑")
                if gs and gm.strip():
                    for grp in groups:
                        if grp["id"]==g["id"]:
                            grp.setdefault("nachrichten",[]).append(
                                dict(von=st.session_state.username,text=gm.strip(),
                                     zeit=datetime.now().strftime("%H:%M")))
                    save_json(GROUPS_FILE,groups); st.rerun()
                if g["erstellt_von"]==st.session_state.username:
                    if st.button("🗑️ Gruppe löschen", key=f"dg_{g['id']}"):
                        groups=[grp for grp in groups if grp["id"]!=g["id"]]
                        save_json(GROUPS_FILE,groups); st.rerun()

# ═══════════════════════════════════════════════════════════
# MARKETPLACE
# ═══════════════════════════════════════════════════════════
elif st.session_state.page == "marketplace":
    market = load_json(MARKET_FILE, DEMO_MARKET)
    chats  = load_json(CHATS_FILE,  DEMO_CHATS)
    sub    = st.tabs(["🏠 Home","🔍 Suche","📦 Verkaufen","💬 Inbox"])

    with sub[0]:
        st.markdown("<div class='kl-section-title'>🛍️ Kunstmarktplatz</div>",
                    unsafe_allow_html=True)
        mk1,mk2 = st.columns(2)
        with mk1: mk = st.selectbox("Kategorie",["Alle","Gemälde","Fotografie","Skulptur","Digital Art","Textil"])
        with mk2: mp = st.slider("Max. Preis (€)",0,5000,5000,step=50)

        items = [i for i in market if i.get("status")!="gelöscht"]
        if mk!="Alle": items=[i for i in items if i["kategorie"]==mk]
        items=[i for i in items if i["preis"]<=mp]

        cols2 = st.columns(2)
        for idx,item in enumerate(items):
            with cols2[idx%2]:
                sc = {"verfügbar":"#22c55e","reserviert":"#f59e0b","verkauft":"#ef4444"}.get(item["status"],"#888")
                st.markdown(f"""
                <div class='kl-card'>
                    <div style='font-size:3rem;text-align:center;
                    background:linear-gradient(135deg,#f4a7b933,#c084fc33);
                    border-radius:12px;padding:16px;margin-bottom:12px'>🖼️</div>
                    <span class='kl-tag'>{item['kategorie']}</span>
                    <span style='background:{sc}22;color:{sc};padding:2px 10px;
                    border-radius:999px;font-size:.72rem;font-weight:700;
                    border:1px solid {sc}55'>{item['status'].upper()}</span>
                    <h4 style='margin:8px 0 4px'>{item['titel']}</h4>
                    <div class='kl-muted'>{item['beschreibung'][:60]}...</div>
                    <div style='margin-top:8px;display:flex;justify-content:space-between'>
                        <span class='kl-price'>💶 {item['preis']} €</span>
                        <span class='kl-muted'>@{item['verkäufer']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Details / Anfragen",key=f"mdet_{item['id']}_{idx}",
                              use_container_width=True):
                    st.session_state.market_item = item["id"]

                if st.session_state.market_item == item["id"]:
                    with st.expander("📄 Details", expanded=True):
                        st.markdown(f"**{item['titel']}**\n\n{item['beschreibung']}")
                        st.markdown(f"- 💶 {item['preis']} €  |  📂 {item['kategorie']}  |  👤 @{item['verkäufer']}")
                        if item["verkäufer"] != st.session_state.username:
                            if st.button("💬 Verkäufer anschreiben",
                                          key=f"msg_{item['id']}"):
                                ck = "__".join(sorted([st.session_state.username,item["verkäufer"]]))
                                if ck not in chats: chats[ck]=[]
                                chats[ck].append(dict(
                                    von=st.session_state.username,
                                    text=f"Hallo! Ich interessiere mich für '{item['titel']}'.",
                                    zeit=datetime.now().strftime("%H:%M")
                                ))
                                save_json(CHATS_FILE,chats)
                                st.success("Nachricht gesendet! → Chats")
                        else:
                            sc1,sc2,sc3 = st.columns(3)
                            for label,status,col in [("✅ Verfügbar","verfügbar",sc1),
                                                      ("⏳ Reserviert","reserviert",sc2),
                                                      ("🔴 Verkauft","verkauft",sc3)]:
                                with col:
                                    if st.button(label,key=f"s{status}_{item['id']}"):
                                        for m in market:
                                            if m["id"]==item["id"]: m["status"]=status
                                        save_json(MARKET_FILE,market); st.rerun()
                            if st.button("🗑️ Löschen",key=f"del_{item['id']}"):
                                market=[m for m in market if m["id"]!=item["id"]]
                                save_json(MARKET_FILE,market)
                                st.session_state.market_item=None; st.rerun()
                        if st.button("✖ Schließen",key=f"mc_{item['id']}"):
                            st.session_state.market_item=None; st.rerun()

    with sub[1]:
        st.markdown("<div class='kl-section-title'>🔍 Suche</div>",
                    unsafe_allow_html=True)
        sq = st.text_input("Was suchst du?",
                            placeholder="z.B. Gemälde, Fotografie, Acryl...")
        if sq:
            market=load_json(MARKET_FILE,DEMO_MARKET)
            res=[i for i in market if sq.lower() in i["titel"].lower()
                 or sq.lower() in i["beschreibung"].lower()
                 or sq.lower() in i["kategorie"].lower()]
            st.markdown(f"**{len(res)} Ergebnis(se)**")
            for item in res:
                st.markdown(f"""
                <div class='kl-card'>
                    <b>{item['titel']}</b> <span class='kl-tag'>{item['kategorie']}</span><br>
                    <span class='kl-muted'>{item['beschreibung'][:80]}...</span><br>
                    <span class='kl-price'>💶 {item['preis']} €</span>
                    <span class='kl-muted'> · @{item['verkäufer']}</span>
                </div>
                """, unsafe_allow_html=True)

    with sub[2]:
        st.markdown("<div class='kl-section-title'>📦 Verkaufen</div>",
                    unsafe_allow_html=True)
        my_items=[i for i in market if i["verkäufer"]==st.session_state.username]
        if my_items:
            st.markdown("**Meine Angebote:**")
            for item in my_items:
                st.markdown(f"""<div class='kl-card'>
                    <b>{item['titel']}</b> · <span class='kl-price'>{item['preis']} €</span>
                    · {item['status']}</div>""", unsafe_allow_html=True)

        st.markdown("---\n**Neuen Artikel einstellen:**")
        with st.form("sell"):
            s1,s2 = st.columns(2)
            with s1:
                st   = st.text_input("Titel")
                skat = st.selectbox("Kategorie",
                                    ["Gemälde","Fotografie","Skulptur","Digital Art","Textil","Sonstiges"])
                sp   = st.number_input("Preis (€)",1,99999,100)
                smat = st.text_input("Material (optional)")
                sgr  = st.text_input("Größe (optional)")
            with s2:
                sbild = st.file_uploader("📸 Bild",type=["jpg","jpeg","png"])
                sdesc = st.text_area("Beschreibung")
                ski   = st.checkbox("✨ KI-Beschreibung generieren")
            sbtn = st.form_submit_button("📦 Einstellen", use_container_width=True)

        if sbtn and st.strip():
            beschr = sdesc.strip()
            if ski and API_VERFUEGBAR and GROQ_API_KEY:
                with st.spinner("🤖 KI schreibt Beschreibung..."):
                    beschr = ki_kunstwerk_beschreibung(st, skat, smat, sgr) or beschr
            bp = None
            if sbild:
                fn = f"{uuid.uuid4()}.{sbild.name.split('.')[-1]}"
                bp = save_media(sbild,"market",fn)
            market.append(dict(
                id=str(uuid.uuid4()),verkäufer=st.session_state.username,
                titel=st.strip(),beschreibung=beschr,kategorie=skat,
                preis=sp,status="verfügbar",bild=bp,
                datum=datetime.now().strftime("%d.%m.%Y")
            ))
            save_json(MARKET_FILE,market)
            st.success(f"✅ '{st}' eingestellt!"); st.rerun()

    with sub[3]:
        st.markdown("<div class='kl-section-title'>💬 Marketplace-Inbox</div>",
                    unsafe_allow_html=True)
        chats=load_json(CHATS_FILE,DEMO_CHATS)
        mc={k:v for k,v in chats.items() if st.session_state.username in k}
        if not mc:
            st.info("Noch keine Nachrichten.")
        else:
            for ck,msgs in mc.items():
                parts=ck.split("__")
                other=next((p for p in parts if p!=st.session_state.username),parts[0])
                oi=next((u for u in DEMO_USERS if u["benutzername"]==other),dict(name=other))
                with st.expander(f"💬 {oi['name']}"):
                    for msg in msgs[-15:]:
                        css="msg-sent" if msg["von"]==st.session_state.username else "msg-recv"
                        st.markdown(f'<div class="{css}">{msg["text"]}</div>',
                                    unsafe_allow_html=True)
                    with st.form(f"ib_{ck}",clear_on_submit=True):
                        ic1,ic2=st.columns([5,1])
                        with ic1: im=st.text_input("...",label_visibility="collapsed")
                        with ic2: isend=st.form_submit_button("↑")
                    if isend and im.strip():
                        chats[ck].append(dict(von=st.session_state.username,
                                              text=im.strip(),
                                              zeit=datetime.now().strftime("%H:%M")))
                        save_json(CHATS_FILE,chats); st.rerun()

# ═══════════════════════════════════════════════════════════
# KONTO / ADMIN
# ═══════════════════════════════════════════════════════════
elif st.session_state.page in ["konto","admin"]:
    if is_admin and st.session_state.page=="admin":
        st.markdown("<div class='kl-section-title'>⚙️ Administration</div>",
                    unsafe_allow_html=True)

        if API_VERFUEGBAR:
            st.markdown("**API-Status:**")
            for name, status in api_status().items():
                st.markdown(f"- {name}: {status}")
            st.markdown("---")

        at1,at2 = st.tabs(["👥 Benutzer","📊 Statistiken"])
        with at1:
            import pandas as pd
            all_acc = load_users() + [u for u in DEMO_USERS]
            st.dataframe(pd.DataFrame([dict(
                Benutzername=u["benutzername"],
                Name=u.get("name",""),Rolle=u.get("rolle","user")
            ) for u in all_acc]), use_container_width=True, hide_index=True)
        with at2:
            posts  = load_json(POSTS_FILE,DEMO_POSTS)
            market = load_json(MARKET_FILE,DEMO_MARKET)
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("👥 Nutzer",   len(load_users())+len(DEMO_USERS))
            m2.metric("📝 Posts",    len(posts))
            m3.metric("🛍️ Artikel",  len(market))
            m4.metric("🗺️ OSM-Orte", len(st.session_state.osm_ergebnisse))

        st.markdown("---")

    # KONTO
    st.markdown("<div class='kl-section-title'>👤 Mein Konto</div>",
                unsafe_allow_html=True)
    users = load_users()
    uo    = next((u for u in users if u["benutzername"]==st.session_state.username), me)

    k1,k2 = st.columns([1,2])
    with k1:
        pp = os.path.join(MEDIA_DIR,"profiles",f"{st.session_state.username}.jpg")
        if os.path.exists(pp):
            st.image(pp, width=120)
        else:
            st.markdown(f"""<div style='width:100px;height:100px;border-radius:50%;
            background:linear-gradient(135deg,#f4a7b9,#c084fc);
            display:flex;align-items:center;justify-content:center;
            color:white;font-size:2.5rem;font-weight:800'>
            {get_avatar_initial(uo.get("name","?"))}</div>""",
                        unsafe_allow_html=True)
        pup = st.file_uploader("📸 Profilbild ändern",
                                type=["jpg","jpeg","png"],key="pup")
        if pup:
            save_media(pup,"profiles",f"{st.session_state.username}.jpg")
            st.success("✅ Gespeichert!"); st.rerun()

    with k2:
        with st.form("pf"):
            pn = st.text_input("Name",  value=uo.get("name",""))
            pb = st.text_area("Bio",    value=uo.get("bio",""), height=80)
            ps = st.form_submit_button("💾 Speichern", use_container_width=True)
        if ps:
            for u in users:
                if u["benutzername"]==st.session_state.username:
                    u["name"]=pn; u["bio"]=pb
            save_users(users); st.success("✅ Profil aktualisiert!")

        posts  = load_json(POSTS_FILE, DEMO_POSTS)
        market = load_json(MARKET_FILE, DEMO_MARKET)
        c1,c2,c3 = st.columns(3)
        c1.metric("📝 Posts",   len([p for p in posts  if p["autor"]==st.session_state.username]))
        c2.metric("🛍️ Artikel", len([m for m in market if m["verkäufer"]==st.session_state.username]))
        c3.metric("⭐ Favoriten",len(load_json(FAVORITES_FILE,{}).get(st.session_state.username,[])))

    st.markdown("---")
    dc,ac = st.columns(2)
    with dc:
        if st.button("🌙 Dunkel-Modus" if not st.session_state.dark_mode else "☀️ Hell-Modus",
                      use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode; st.rerun()
    with ac:
        if st.button("🚪 Abmelden", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown("""<div style='text-align:center;color:#aaa;font-size:.78rem'>
kultur· · Powered by OpenStreetMap 🗺️ · Ticketmaster 🎭 · Groq/LLaMA 🤖 · v2.1
</div>""", unsafe_allow_html=True)
