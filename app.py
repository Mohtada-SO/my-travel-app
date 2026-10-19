import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os, base64
import math
import requests
from datetime import datetime, time, timedelta, date

st.set_page_config(page_title="Smart Travel Atlas | Southampton", page_icon="🌿", layout="wide")

# === SECTION 1: PREMIUM VISUAL SYSTEM (CSS & DARK-MODE FIX) ===
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap');

    .stApp {
        background-color: #FAF8F5 !important;
        color: #1F2421 !important;
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3, .serif-title {
        font-family: 'Playfair Display', serif !important;
        color: #1B4332 !important;
        letter-spacing: -0.01em;
    }
    
    /* Force readable dark text even when phone/browser is in Dark Mode */
    .stMarkdown, p, span, label, li, div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"] {
        color: #1F2421 !important;
    }
    .dest-body h4, .dest-body div {
        color: #1F2421 !important;
    }
    input, textarea {
        color: #1F2421 !important;
        background-color: #FFFFFF !important;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #F2EFE9 !important;
        border-right: 1px solid #E5E0D8;
    }

    .hero-box {
        position: relative;
        border-radius: 18px;
        overflow: hidden;
        background-image: linear-gradient(180deg, rgba(20, 35, 28, 0.25) 0%, rgba(20, 35, 28, 0.82) 100%), 
                          url('https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Durdle_Door_Overview.jpg/1280px-Durdle_Door_Overview.jpg');
        background-size: cover;
        background-position: center;
        padding: 52px 42px;
        color: #FAF8F5 !important;
        margin-bottom: 26px;
        box-shadow: 0 12px 30px rgba(27, 67, 50, 0.12);
    }
    .hero-tag {
        background: rgba(250, 248, 245, 0.22);
        backdrop-filter: blur(6px);
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        color: #FFFFFF !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        display: inline-block;
        margin-bottom: 12px;
    }
    .hero-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.5rem;
        font-weight: 700;
        color: #FFFFFF !important;
        margin: 0 0 10px 0;
        line-height: 1.15;
    }
    .hero-sub {
        font-size: 1.02rem;
        color: #F0F4F1 !important;
        max-width: 640px;
        font-weight: 300;
        margin-bottom: 0;
    }

    .stat-card {
        background: #FFFFFF;
        border: 1px solid #EAE6DF;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.02);
    }
    .stat-label { font-size: 0.78rem; color: #5C6660 !important; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
    .stat-val { font-size: 1.7rem; font-weight: 700; color: #1B4332 !important; margin: 6px 0 2px 0; }
    .stat-sub { font-size: 0.82rem; color: #2D6A4F !important; }

    .dest-card {
        background: #FFFFFF;
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid #EAE6DF;
        box-shadow: 0 6px 18px rgba(0,0,0,0.03);
        margin-bottom: 14px;
    }
    .dest-img {
        width: 100%;
        height: 195px;
        object-fit: cover;
    }
    .dest-body { padding: 16px 18px; }
    .badge-visited { background: #D8F3DC; color: #1B4332 !important; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .badge-wishlist { background: #FFF3CD; color: #856404 !important; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .badge-trust { background: #E6F2EF; color: #1F5E55 !important; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; margin-left: 5px; }
</style>
""", unsafe_allow_html=True)

# === SECTION 2: DATA & HELPER FUNCTIONS ===
DATA_FILE = "travel_atlas_v5.json"
SOU_LAT, SOU_LON = 50.9097, -1.4044

def calc_distance_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = math.sin(math.radians(lat2 - lat1)/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(math.radians(lon2 - lon1)/2)**2
    return round(R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))))

@st.cache_data(ttl=1800)
def get_live_weather_and_sunset(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m&daily=sunset,precipitation_probability_max&timezone=auto"
        r = requests.get(url, timeout=4).json()
        return {
            "temp": r["current"]["temperature_2m"],
            "wind": r["current"]["wind_speed_10m"],
            "rain_prob": r["daily"]["precipitation_probability_max"][0],
            "sunset": r["daily"]["sunset"][0].split("T")[1],
            "ok": True
        }
    except:
        return {"ok": False}

@st.cache_data(ttl=86400)
def auto_lookup_place(query):
    out = {"ok": False, "lat": 50.9097, "lon": -1.4044, "dist": 50, "img": "", "summary": "", "name": query, "region": "UK"}
    try:
        headers = {"User-Agent": "SmartTravelAtlas/3.0"}
        # 1. Geocode first to get exact city/region context
        r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": query, "format": "json", "addressdetails": 1, "limit": 1}, headers=headers, timeout=5).json()
        wiki_query = f"{query} city town landmark"
        if r:
            out["lat"], out["lon"] = float(r[0]["lat"]), float(r[0]["lon"])
            out["dist"] = calc_distance_km(SOU_LAT, SOU_LON, out["lat"], out["lon"])
            out["ok"] = True
            parts = [p.strip() for p in r[0].get("display_name", "").split(",")]
            if len(parts) >= 2:
                out["name"] = parts[0]
                out["region"] = f"{parts[1]}, {parts[-1]}"
                wiki_query = f"{parts[0]} {parts[1]} {parts[-1]}"

        # 2. Search Wikipedia using the full geographic context (prevents 'Bath' -> bathtub!)
        sr = requests.get("https://en.wikipedia.org/w/api.php", params={
            "action": "query", "list": "search", "srsearch": wiki_query, "format": "json", "srlimit": 1
        }, headers=headers, timeout=4).json()
        hits = sr.get("query", {}).get("search", [])
        if hits:
            title = hits[0]["title"].replace(" ", "_")
            w = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}", headers=headers, timeout=4).json()
            if "thumbnail" in w: out["img"] = w["thumbnail"]["source"]
            if "extract" in w: out["summary"] = w["extract"][:200] + "..."
    except:
        pass
    return out

def calc_schengen_rolling(trips, ref_date=None):
    ref_date = ref_date or date.today()
    win_start = ref_date - timedelta(days=179)
    used = set()
    for t in trips:
        try:
            curr, end = datetime.strptime(t["start"], "%Y-%m-%d").date(), datetime.strptime(t["end"], "%Y-%m-%d").date()
            while curr <= end:
                if win_start <= curr <= ref_date: used.add(curr)
                curr += timedelta(days=1)
        except:
            pass
    return len(used), win_start

DEFAULT_DATA = {
    "owner_pin": "",
    "uk_airports": [
        {"name": "Bournemouth (BOH)", "transit_gbp": 8.0, "info": "45m (Train + Bus)"},
        {"name": "Southampton (SOU)", "transit_gbp": 5.5, "info": "10m (Direct Train)"},
        {"name": "Bristol (BRS) ⭐", "transit_gbp": 24.0, "info": "1h 45m (Train + Flyer)"},
        {"name": "London Gatwick (LGW)", "transit_gbp": 26.0, "info": "2h (Direct Train/Coach)"},
        {"name": "London Luton / Stansted", "transit_gbp": 38.0, "info": "3h (Train + Coach)"},
        {"name": "Birmingham (BHX)", "transit_gbp": 32.0, "info": "2h 30m (Direct Train)"}
    ],
    "places": [
        {
            "id": 1, "name": "Durdle Door & Lulworth Cove", "region": "Dorset, England", "scope": "UK",
            "category": "Coastal Walk", "community_tag": "Jurassic Coast Trust / SW Coast Path", "status": "wishlist",
            "lat": 50.6212, "lon": -2.2768, "distance_km": 69, "rating": 5, "paid_gbp": 16.20, "saved_gbp": 8.50,
            "saving_hack": "SWR Railcard Return to Wool + £2 Morebus Cap",
            "dep_time": "09:00", "transit_mins": 85, "activity_hours": 4.0, "last_return": "17:15",
            "last_transit_note": "Morebus 30 to Wool Station ends early in autumn/winter!",
            "payment_rule": "Contactless OK (Tap Off on exit!)", "ticket_info": "Free beach & cliff path access",
            "highlights": "Limestone sea arch, Stair Hole folded rocks, Lulworth Cove",
            "notes": "Train from Southampton Central to Wool, then Morebus 30.",
            "source_link": "https://www.alltrails.com/en-gb/trail/england/dorset/durdle-door-and-lulworth-cove",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Durdle_Door_Overview.jpg/1024px-Durdle_Door_Overview.jpg",
            "checkpoints": [{"task": "Train Southampton -> Wool Station", "done": False}, {"task": "Morebus 30 to Durdle Door", "done": False}]
        },
        {
            "id": 2, "name": "South Downs Way (Hassocks to Lewes)", "region": "East Sussex, England", "scope": "UK",
            "category": "Linear Hike (17 km)", "community_tag": "National Trust (Ditchling Beacon)", "status": "wishlist",
            "lat": 50.9086, "lon": -0.1072, "distance_km": 92, "rating": 5, "paid_gbp": 20.70, "saved_gbp": 18.00,
            "saving_hack": "Off-Peak Return to Lewes + short Single (Brighton-Hassocks)",
            "dep_time": "08:30", "transit_mins": 132, "activity_hours": 4.5, "last_return": "21:02",
            "last_transit_note": "Sunset ~18:05! Last direct Brighton->Southampton train at 21:02",
            "payment_rule": "Railcard on App | Emergency Breeze Bus 79 at Beacon (£2 Card)",
            "ticket_info": "Free National Trail - Bring 2L water (no shops on ridge)",
            "highlights": "Jack & Jill Windmills, Ditchling Beacon 360° summit, Lewes Castle",
            "notes": "Station-to-station linear hike across the South Downs chalk ridge.",
            "source_link": "https://www.alltrails.com/en-gb/trail/england/west-sussex/hassocks-to-lewes",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/South_Downs_Way_near_Ditchling_Beacon.jpg/1024px-South_Downs_Way_near_Ditchling_Beacon.jpg",
            "checkpoints": [{"task": "08:30 train to Hassocks (Exit Platform 2)", "done": False}, {"task": "Climb Jack & Jill Windmills to Ditchling Beacon", "done": False}]
        },
        {
            "id": 3, "name": "Shaftesbury & Gold Hill", "region": "Dorset, England", "scope": "UK",
            "category": "Historic Hilltop Town", "community_tag": "English Heritage / Dorset AONB", "status": "visited",
            "lat": 51.0045, "lon": -2.1983, "distance_km": 68, "rating": 5, "paid_gbp": 14.50, "saved_gbp": 12.00,
            "saving_hack": "Railcard 1/3 off to Gillingham + £2 Bus Cap",
            "dep_time": "09:30", "transit_mins": 95, "activity_hours": 3.5, "last_return": "17:38",
            "last_transit_note": "Last bus (X2/B3) to Gillingham Station at 17:38!",
            "payment_rule": "Contactless / Apple Pay accepted on bus", "ticket_info": "Free 24/7 access to Gold Hill",
            "highlights": "Iconic cobbled Gold Hill street, Blackmore Vale panoramic views",
            "notes": "Train to Gillingham (Dorset) then local bus.", "source_link": "",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Gold_Hill%2C_Shaftesbury.jpg/1024px-Gold_Hill%2C_Shaftesbury.jpg",
            "checkpoints": [{"task": "Train to Gillingham & Bus to Shaftesbury", "done": True}]
        },
        {
            "id": 4, "name": "Bath (Roman Baths & Royal Crescent)", "region": "Somerset, England", "scope": "UK",
            "category": "Historic Heritage City", "community_tag": "UNESCO World Heritage / National Trust Skyline", "status": "wishlist",
            "lat": 51.3811, "lon": -2.3590, "distance_km": 84, "rating": 5, "paid_gbp": 19.80, "saved_gbp": 10.00,
            "saving_hack": "Direct GWR Train from Southampton Central with Railcard (1h 25m - No changes!)",
            "dep_time": "09:10", "transit_mins": 85, "activity_hours": 5.5, "last_return": "22:20",
            "last_transit_note": "Direct GWR trains back to Southampton run hourly until ~22:20 from Bath Spa!",
            "payment_rule": "Contactless OK everywhere | Show Railcard on GWR train",
            "ticket_info": "City & Pulteney Bridge free | Roman Baths: Book student ticket online",
            "highlights": "Roman Baths, Royal Crescent, Pulteney Bridge, National Trust Bath Skyline walk",
            "notes": "Super easy direct train day-trip from Southampton Central.",
            "source_link": "https://www.nationaltrust.org.uk/visit/bath-bristol/bath-skyline",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Pulteney_Bridge_Bath.jpg/1024px-Pulteney_Bridge_Bath.jpg",
            "checkpoints": [{"task": "Direct GWR train Southampton -> Bath Spa", "done": False}, {"task": "Walk Pulteney Bridge & Royal Crescent", "done": False}]
        },
        {
            "id": 5, "name": "Girona / Costa Brava (Extreme Day Trip)", "region": "Spain", "scope": "Europe",
            "category": "Extreme Day Trip (EDT)", "community_tag": "Ryanair Cheap Escape", "status": "wishlist",
            "lat": 41.9794, "lon": 2.8214, "distance_km": 1050, "rating": 5, "paid_gbp": 29.00, "saved_gbp": 45.00,
            "saving_hack": "£18 Return Flight from Bournemouth (BOH) - No hotel needed!",
            "dep_time": "06:30", "transit_mins": 120, "activity_hours": 9.0, "last_return": "21:45",
            "last_transit_note": "Airport Bus to Girona Centre takes 20 mins (€2.75)",
            "payment_rule": "Contactless OK on Girona buses; validate paper rail tickets!",
            "ticket_info": "Medieval walls walk is free!",
            "highlights": "Game of Thrones medieval streets, Onyar River houses, Spanish tapas",
            "notes": "Direct cheap flight from Bournemouth Airport.", "source_link": "",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/Cases_de_l%27Onyar_%28Girona%29.jpg/1024px-Cases_de_l%27Onyar_%28Girona%29.jpg",
            "checkpoints": [{"task": "Bus/Train to Bournemouth Airport (BOH)", "done": False}]
        }
    ],
    "expenses": [
        {"date": "2026-10-16", "trip": "Shaftesbury", "item": "Train to Gillingham", "amount_gbp": 10.50, "category": "Transit"},
        {"date": "2026-10-16", "trip": "Shaftesbury", "item": "Return Bus X2", "amount_gbp": 4.00, "category": "Transit"}
    ],
    "schengen_trips": [
        {"country": "Italy (Milan)", "start": "2026-06-10", "end": "2026-06-16"}
    ]
}

def load_data():
    gh_token = st.secrets.get("GITHUB_TOKEN", "")
    gh_repo = st.secrets.get("GITHUB_REPO", "Mohtada-SO/my-travel-app")
    # 1. Try loading permanent file directly from GitHub first
    if gh_token:
        try:
            url = f"https://api.github.com/repos/{gh_repo}/contents/{DATA_FILE}"
            r = requests.get(url, headers={"Authorization": f"token {gh_token}"}, timeout=5)
            if r.status_code == 200:
                content = base64.b64decode(r.json()["content"]).decode("utf-8")
                d = json.loads(content)
                with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)
                return d
        except: pass
    # 2. Fallback to local file
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(DEFAULT_DATA, f, ensure_ascii=False, indent=2)
    with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_data(d):
    content_str = json.dumps(d, ensure_ascii=False, indent=2)
    with open(DATA_FILE, "w", encoding="utf-8") as f: f.write(content_str)
    # Auto-sync to GitHub permanently
    gh_token = st.secrets.get("GITHUB_TOKEN", "")
    gh_repo = st.secrets.get("GITHUB_REPO", "Mohtada-SO/my-travel-app")
    if gh_token:
        try:
            url = f"https://api.github.com/repos/{gh_repo}/contents/{DATA_FILE}"
            headers = {"Authorization": f"token {gh_token}"}
            r = requests.get(url, headers=headers, timeout=5)
            sha = r.json().get("sha") if r.status_code == 200 else None
            payload = {
                "message": "Auto-save travel atlas data",
                "content": base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
            }
            if sha: payload["sha"] = sha
            requests.put(url, headers=headers, json=payload, timeout=6)
        except: pass

data = load_data()

# --- Permanent Owner Lock Check (from Streamlit Secrets or JSON) ---
secret_pin = str(st.secrets.get("OWNER_PIN", "") or data.get("owner_pin", ""))
pin_set = bool(secret_pin)
if "is_owner" not in st.session_state: st.session_state.is_owner = not pin_set
# --- Owner Lock Check ---
pin_set = bool(data.get("owner_pin", ""))
if "is_owner" not in st.session_state: st.session_state.is_owner = not pin_set

with st.sidebar:
    st.markdown("## 🌿 Smart Travel Atlas")
    st.caption("Southampton Hub • UK & Europe")
    if "nav_page" not in st.session_state: st.session_state.nav_page = "🏡 Home & Inspiration"
    nav_options = [
        "🏡 Home & Inspiration",
        "🗺️ Explore & Pin Map",
        "🇬🇧 Trip & Hike Planner",
        "✈️ Europe, Airports & EDT",
        "➕ Add Place / Social Link",
        "💸 Expenses & Schengen",
        "⚙️ Settings, Lock & Backup"
    ]
    page = st.radio("Navigation", nav_options, index=nav_options.index(st.session_state.nav_page) if st.session_state.nav_page in nav_options else 0)
    st.session_state.nav_page = page
    st.divider()
    if pin_set and not st.session_state.is_owner:
        u_pin = st.text_input("🔒 Visitor Mode (Enter Owner PIN to Edit):", type="password")
        if u_pin == data["owner_pin"]: st.session_state.is_owner = True; st.rerun()
    else:
        st.caption("🔓 **Owner Mode Active** (Full Edit Enabled)")

can_edit = st.session_state.is_owner

# === PAGE 1: HOME ===
if page == "🏡 Home & Inspiration":
    c_top1, c_top2, c_top3 = st.columns([3.5, 1, 1])
    c_top1.markdown("### 🌿 Smart Travel Planner & Memory Atlas")
    if c_top2.button("🇬🇧 Plan Trip", use_container_width=True): st.session_state.nav_page = "🇬🇧 Trip & Hike Planner"; st.rerun()
    if c_top3.button("✈️ Europe / EDT", use_container_width=True): st.session_state.nav_page = "✈️ Europe, Airports & EDT"; st.rerun()

    st.markdown("""
    <div class="hero-box">
        <div class="hero-tag">⚓ Base Hub: Southampton, UK</div>
        <div class="hero-title">British Heritage Trails & European Escapes.</div>
        <p class="hero-sub">Plan scenic railway hikes, discover National Trust coastlines, hunt £18 extreme day trips, and preserve every memory.</p>
    </div>
    """, unsafe_allow_html=True)

    visited = [p for p in data["places"] if p["status"] == "visited"]
    uk_count = len([p for p in data["places"] if p.get("scope", "UK") == "UK"])
    eu_count = len([p for p in data["places"] if p.get("scope") == "Europe"])
    total_spent = sum(e.get("amount_gbp", 0) for e in data["expenses"])
    used_sch, _ = calc_schengen_rolling(data.get("schengen_trips", []))

    s1, s2, s3, s4 = st.columns(4)
    s1.markdown(f"""<div class="stat-card"><div class="stat-label">Atlas Collection</div><div class="stat-val">{len(visited)} / {len(data['places'])}</div><div class="stat-sub">{uk_count} UK • {eu_count} Europe</div></div>""", unsafe_allow_html=True)
    s2.markdown(f"""<div class="stat-card"><div class="stat-label">Distance Explored</div><div class="stat-val">{sum(p.get('distance_km',0)*2 for p in visited)} km</div><div class="stat-sub">From Southampton Hub</div></div>""", unsafe_allow_html=True)
    s3.markdown(f"""<div class="stat-card"><div class="stat-label">Total Spent</div><div class="stat-val">£{total_spent:.2f}</div><div class="stat-sub">Saved £{sum(p.get('saved_gbp',0) for p in data['places']):.2f} smart hacks</div></div>""", unsafe_allow_html=True)
    s4.markdown(f"""<div class="stat-card"><div class="stat-label">Schengen Quota</div><div class="stat-val">{90 - used_sch} Days Left</div><div class="stat-sub">{used_sch}/90 used (Rolling 180d)</div></div>""", unsafe_allow_html=True)

    st.write("")
    f_scope = st.radio("Show Destinations:", ["All Journeys", "🇬🇧 UK Internal Trips", "✈️ Europe & Extreme Day Trips"], horizontal=True)
    filtered_p = [p for p in data["places"] if f_scope == "All Journeys" or (f_scope.startswith("🇬🇧") and p.get("scope","UK")=="UK") or (f_scope.startswith("✈️") and p.get("scope")=="Europe")]

    if can_edit and st.button("🧹 Clean Duplicate Cities Automatically"):
        seen = set()
        unique_places = []
        for p in data["places"]:
            if p["name"].strip().lower() not in seen:
                seen.add(p["name"].strip().lower())
                unique_places.append(p)
        data["places"] = unique_places
        save_data(data)
        st.success("Removed all duplicate cities!")
        st.rerun()

    FALLBACK_IMG = "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=900&q=80"
    cols = st.columns(3)
    for idx, p in enumerate(filtered_p):
        with cols[idx % 3]:
            b_cls = "badge-visited" if p["status"] == "visited" else "badge-wishlist"
            b_txt = "✓ Visited" if p["status"] == "visited" else "✦ Wishlist"
            img = p.get("image_url") if p.get("image_url") else FALLBACK_IMG
            st.markdown(f"""
            <div class="dest-card">
                <img src="{img}" onerror="this.onerror=null;this.src='{FALLBACK_IMG}';" class="dest-img">
                <div class="dest-body">
                    <span class="{b_cls}">{b_txt}</span> <span class="badge-trust">{p.get('scope','UK')} • {p.get('community_tag','Nature')[:22]}</span>
                    <h4 style="margin:10px 0 4px 0;">{p['name']}</h4>
                    <div style="font-size:0.8rem; color:#6B756E; margin-bottom:8px;">📍 {p.get('region','')} • {p['distance_km']} km from SOU</div>
                    <div style="font-size:0.83rem; background:#F7F5F0; padding:8px; border-radius:8px; margin-bottom:8px;"><b>👀 Highlights:</b> {p.get('highlights','')[:80]}</div>
                    <div style="font-size:0.78rem; color:#854D0E;">🚨 <b>Curfew:</b> {p['last_return']} | 💳 {p['payment_rule'][:28]}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            bc1, bc2 = st.columns([3, 1])
            if bc1.button(f"Open: {p['name'][:18]}", key=f"hb_{idx}_{p['id']}", use_container_width=True):
                st.session_state.selected_place = p["name"]
                st.session_state.nav_page = "🇬🇧 Trip & Hike Planner"
                st.rerun()
            if can_edit and bc2.button("🗑️", key=f"del_{idx}_{p['id']}", help="Delete this place", use_container_width=True):
                data["places"].pop(data["places"].index(p))
                save_data(data)
                st.rerun()

# === PAGE 2: FULL INTERACTIVE MAP ===
elif page == "🗺️ Explore & Pin Map":
    st.markdown("## 🗺️ Interactive Memory & Wishlist Atlas")
    mf1, mf2 = st.columns(2)
    f_stat = mf1.radio("Status:", ["All", "Visited (Green)", "Wishlist (Orange)"], horizontal=True)
    f_reg = mf2.radio("Region:", ["All (UK & Europe)", "🇬🇧 UK Only", "✈️ Europe Only"], horizontal=True)
    zoom = 5 if f_reg == "✈️ Europe Only" else (8 if f_reg == "🇬🇧 UK Only" else 6)
    m = folium.Map(location=[SOU_LAT, SOU_LON], zoom_start=zoom)
    folium.Marker([SOU_LAT, SOU_LON], tooltip="🏠 Southampton Base Hub", icon=folium.Icon(color="black", icon="home")).add_to(m)
    for p in data["places"]:
        if f_stat == "Visited (Green)" and p["status"] != "visited": continue
        if f_stat == "Wishlist (Orange)" and p["status"] == "visited": continue
        if f_reg == "🇬🇧 UK Only" and p.get("scope","UK") != "UK": continue
        if f_reg == "✈️ Europe Only" and p.get("scope") != "Europe": continue
        col = "green" if p["status"] == "visited" else "orange"
        folium.Marker([p["lat"], p["lon"]], popup=f"<b>{p['name']}</b><br>Curfew: {p['last_return']}<br>{p.get('highlights','')}", tooltip=p["name"], icon=folium.Icon(color=col)).add_to(m)
    st_folium(m, width=1050, height=520, returned_objects=[])

# === PAGE 3: TRIP & HIKE PLANNER (ALL DESTINATIONS) ===
elif page == "🇬🇧 Trip & Hike Planner":
    st.markdown("## 🧭 Interactive Trip, Trail & Curfew Planner")
    names = [p["name"] for p in data["places"]]
    idx = names.index(st.session_state.get("selected_place")) if st.session_state.get("selected_place") in names else 0
    sel = st.selectbox("Select Destination to Plan or Edit:", names, index=idx)
    place = next(p for p in data["places"] if p["name"] == sel)

    col_l, col_r = st.columns([1.05, 1.45])
    with col_l:
        if place.get("image_url"):
            st.image(place.get("image_url"), use_container_width=True)
        if can_edit and st.button("🔄 Toggle Visited / Wishlist Status", use_container_width=True):
            place["status"] = "visited" if place["status"] != "visited" else "wishlist"; save_data(data); st.rerun()
        st.info(f"🏛️ **Trust / Tag:** {place.get('community_tag','')}\n\n👀 **What You'll See:** {place.get('highlights','')}\n\n📝 **Notes:** {place.get('notes','')}")
        
        q_clean = place["name"].split("(")[0].strip().replace(" ", "+")
        b1, b2, b3 = st.columns(3)
        b1.link_button("🚆 Check Live Last Train/Bus", f"https://www.google.com/maps/dir/{q_clean}/Southampton+Central/data=!4m2!4m1!3e3", use_container_width=True)
        b2.link_button("🥾 Trail / Source Link", place.get("source_link") or f"https://www.alltrails.com/search?q={q_clean}", use_container_width=True)
        b3.link_button("🏛️ Heritage & Tickets", f"https://www.google.com/search?q={q_clean}+official+tickets+national+trust", use_container_width=True)

    with col_r:
        w = get_live_weather_and_sunset(place["lat"], place["lon"])
        if w.get("ok"):
            w1, w2, w3 = st.columns(3)
            w1.metric("🌡️ Live Temp", f"{w['temp']}°C"); w2.metric("🌧️ Rain Prob", f"{w['rain_prob']}%"); w3.metric("🌅 Sunset Today", w["sunset"])

        st.markdown("#### ⏱️ Reverse Timeline & Last-Bus Curfew Calculator")
        tc1, tc2, tc3, tc4 = st.columns(4)
        try:
            d_dep = datetime.strptime(place.get("dep_time","08:30"),"%H:%M").time()
            d_lr = datetime.strptime(place.get("last_return","18:00"),"%H:%M").time()
        except:
            d_dep, d_lr = time(8,30), time(18,0)
        dep_t = tc1.time_input("Leave SOU:", d_dep)
        tr_m = tc2.number_input("Transit (m):", value=int(place.get("transit_mins",90)), step=5)
        ac_h = tc3.number_input("Walk/Stay (h):", value=float(place.get("activity_hours",4.0)), step=0.5)
        lr_t = tc4.time_input("🚨 Last Return:", d_lr)

        arr_dt = datetime.combine(date.today(), dep_t) + timedelta(minutes=tr_m)
        fin_dt = arr_dt + timedelta(hours=ac_h)
        buf_m = int((datetime.combine(date.today(), lr_t) - fin_dt).total_seconds() / 60)
        st.write(f"**Arrive:** `{arr_dt.strftime('%H:%M')}` ➡️ **Finish Walk:** `{fin_dt.strftime('%H:%M')}` ➡️ **Last Return:** `{lr_t.strftime('%H:%M')}`")
        if buf_m >= 45: st.success(f"✅ Safe Schedule! {buf_m//60}h {buf_m%60}m spare buffer before curfew.")
        else: st.error(f"⚠️ Tight/Danger! Buffer is {buf_m} mins. Leave Southampton earlier!")

        st.error(f"🚌 **Curfew Warning:** {place['last_transit_note']}")
        st.warning(f"💳 **Local Payment Rule:** {place['payment_rule']} | 🎟️ **Tickets:** {place['ticket_info']}")
        st.success(f"💡 **Smart Hack:** {place.get('saving_hack','')} (Saved £{place.get('saved_gbp',0)})")

        st.markdown("#### ☑️ Trip Checkpoints")
        for i, cp in enumerate(place.get("checkpoints", [])):
            chk = st.checkbox(cp["task"], value=cp["done"], key=f"cp_{place['id']}_{i}", disabled=not can_edit)
            if chk != cp["done"]: place["checkpoints"][i]["done"] = chk; save_data(data)
        if can_edit:
            ncp = st.text_input("Add checkpoint step:", placeholder="e.g., Buy water at station")
            if st.button("➕ Add Step") and ncp: place.setdefault("checkpoints",[]).append({"task":ncp,"done":False}); save_data(data); st.rerun()

        if can_edit:
            with st.expander("✏️ Edit Trip Details, Photo, Curfew & Delete"):
                place["image_url"] = st.text_input("Image URL:", place.get("image_url",""))
                place["highlights"] = st.text_area("What You'll See (Highlights):", place.get("highlights",""))
                place["last_transit_note"] = st.text_input("Last Bus/Train Note:", place.get("last_transit_note",""))
                place["payment_rule"] = st.text_input("Payment Rule:", place.get("payment_rule",""))
                place["saving_hack"] = st.text_input("Smart Saving Hack:", place.get("saving_hack",""))
                place["paid_gbp"] = st.number_input("Paid (£):", value=float(place.get("paid_gbp",0.0)))
                place["saved_gbp"] = st.number_input("Saved (£):", value=float(place.get("saved_gbp",0.0)))
                c_sv, c_dl = st.columns(2)
                if c_sv.button("💾 Save All Changes", use_container_width=True):
                    place["dep_time"], place["transit_mins"], place["activity_hours"], place["last_return"] = dep_t.strftime("%H:%M"), tr_m, ac_h, lr_t.strftime("%H:%M")
                    save_data(data); st.success("Saved!"); st.rerun()
                if c_dl.button("🗑️ Delete This Destination", use_container_width=True):
                    data["places"] = [p for p in data["places"] if p["id"] != place["id"]]
                    save_data(data); st.rerun()

# === PAGE 4: EUROPE, DYNAMIC AIRPORTS & EXTREME DAY TRIPS (EDT) ===
elif page == "✈️ Europe, Airports & EDT":
    st.markdown("## ✈️ Europe Escapes, Custom Airport Matrix & Extreme Day Trips")
    st.markdown("### ⚡ 1. Spontaneous 'Extreme Day Trip' (EDT) Cheap Flight Hunter")
    st.caption("Find £15–£25 return flights from airports near Southampton:")
    e1, e2, e3, e4 = st.columns(4)
    e1.link_button("🔥 From Bournemouth (BOH)", "https://www.skyscanner.net/transport/flights-from/boh/", use_container_width=True)
    e2.link_button("⭐ From Bristol (BRS)", "https://www.skyscanner.net/transport/flights-from/brs/", use_container_width=True)
    e3.link_button("✈️ From Gatwick (LGW)", "https://www.skyscanner.net/transport/flights-from/lgw/", use_container_width=True)
    e4.link_button("🎒 Ryanair Fare Finder", "https://www.ryanair.com/gb/en/cheap-flights", use_container_width=True)

    st.divider()
    st.markdown("### 🧮 2. Door-to-Door Airport Comparator (Custom Per City)")
    c_city, c_dest_bus = st.columns([2, 1])
    target_city = c_city.text_input("🌍 Which European City are you comparing flights for?", "Girona / Barcelona, Spain")
    dest_transfer = c_dest_bus.number_input("🚌 Euro Airport -> City Centre Return Bus/Train (£):", value=6.0, step=1.0)

    cols = st.columns(3)
    ap_results = []
    for i, ap in enumerate(data["uk_airports"]):
        with cols[i % 3]:
            fl = st.number_input(f"✈️ Flight from {ap['name']} (£):", value=22.0 if i==0 else 29.0, step=1.0, key=f"ap_{i}")
            real_total = fl + ap["transit_gbp"] + dest_transfer
            ap_results.append({"UK Airport": ap["name"], "Flight (£)": fl, "SOU->Airport Return (£)": ap["transit_gbp"], "EU Airport->City (£)": dest_transfer, "REAL DOOR-TO-DOOR TOTAL (£)": real_total, "Transit Info": ap["info"]})
    
    ap_results.sort(key=lambda x: x["REAL DOOR-TO-DOOR TOTAL (£)"])
    win = ap_results[0]
    st.success(f"🏆 **Cheapest Door-to-Door Route to {target_city}: {win['UK Airport']}** — Total: **£{win['REAL DOOR-TO-DOOR TOTAL (£)']:.2f}**")
    st.dataframe(ap_results, use_container_width=True)

    if can_edit:
        with st.expander("➕ Add Another UK Airport to Your Permanent Matrix"):
            na_name = st.text_input("Airport Name (e.g., Manchester MAN or Exeter EXT):")
            na_cost = st.number_input("Return Transit Cost from Southampton (£):", value=35.0)
            na_info = st.text_input("Transit Time/Method:", "3h Train")
            if st.button("Add Airport to Matrix") and na_name:
                data["uk_airports"].append({"name": na_name, "transit_gbp": na_cost, "info": na_info}); save_data(data); st.rerun()

# === PAGE 5: UNIVERSAL PLACE & SOCIAL LINK IMPORTER ===
elif page == "➕ Add Place / Social Link":
    st.markdown("## ➕ Universal Destination & Social Media Importer")
    if not can_edit:
        st.warning("🔒 Owner Lock is active. Unlock in the sidebar to add new places.")
    else:
        col_s, col_j = st.columns([1.3, 1])
        with col_s:
            st.subheader("🔍 1. Smart Geo-Fetch (Wikipedia + Map + Social Link)")
            st.caption("Type a city, village, or landmark (e.g., 'Bath, UK' or 'Corfe Castle'). It finds the exact location first so Wikipedia fetches the real place!")
            q_search = st.text_input("Place or City Name:", placeholder="e.g., Bath, UK OR Zaragoza, Spain")
            if "lookup" not in st.session_state: st.session_state.lookup = {"name":"", "region":"UK", "lat":50.9097, "lon":-1.4044, "dist":50, "img":"", "summary":""}
            if st.button("🔍 Auto-Fetch Place Info & Photo") and q_search:
                res = auto_lookup_place(q_search)
                st.session_state.lookup = res
                if res["ok"]: st.success(f"Found: {res['name']} ({res['region']}) — {res['dist']} km from Southampton!")
                else: st.warning("Could not auto-locate. Try adding ', UK' or country name.")

            lk = st.session_state.lookup
            if lk.get("name"):
                q_tr = lk["name"].replace(" ", "+")
                st.link_button(f"🚆 Click to check live train/bus times from Southampton to {lk['name']}", f"https://www.google.com/maps/dir/Southampton+Central/{q_tr}/data=!4m2!4m1!3e3")

            with st.form("add_uni_form"):
                f_name = st.text_input("Destination Title:", value=lk.get("name") or q_search)
                f_reg_txt = st.text_input("Region / Country:", value=lk.get("region", "UK"))
                f_scope = st.selectbox("Trip Scope:", ["UK", "Europe"])
                f_cat = st.selectbox("Category:", ["Historic Village / City", "Linear Hike / Nature", "Coastal Walk", "Extreme Day Trip (EDT)", "Food & Cafe Spot"])
                f_trust = st.text_input("Community / Trust / Airline Tag:", "National Trust / GWR / Ryanair")
                f_link = st.text_input("🔗 Source Link (Instagram, TikTok, AllTrails, Google Maps, Blog):")
                f_high = st.text_area("👀 What You'll See (Highlights):", value=lk.get("summary",""))
                f_img = st.text_input("Photo URL (Auto-filled from Wikipedia):", value=lk.get("img",""))
                c1, c2 = st.columns(2)
                f_last = c1.text_input("🚨 Last Return Bus/Train/Flight (HH:MM):", "20:30")
                f_pay = c2.text_input("💳 Local Payment Rule:", "Contactless OK")
                
                if st.form_submit_button("📌 Save Destination to My Atlas"):
                    if f_name:
                        data["places"].append({
                            "id": int(datetime.now().timestamp()), "name": f_name, "region": f_reg_txt, "scope": f_scope,
                            "category": f_cat, "community_tag": f_trust, "status": "wishlist",
                            "lat": lk["lat"], "lon": lk["lon"], "distance_km": lk["dist"], "rating": 5,
                            "paid_gbp": 0.0, "saved_gbp": 0.0, "saving_hack": "", "dep_time": "08:30",
                            "transit_mins": 90, "activity_hours": 4.0, "last_return": f_last,
                            "last_transit_note": f"Last return at {f_last}", "payment_rule": f_pay,
                            "ticket_info": "Check official website", "highlights": f_high, "notes": "",
                            "source_link": f_link, "image_url": f_img, "checkpoints": []
                        })
                        save_data(data); st.success(f"Added {f_name}!"); st.rerun()

        with col_j:
            st.subheader("🤖 2. Quick AI JSON Paste")
            st.caption("Ask me in chat for any city/village and I'll give you a ready JSON with exact last bus times & ticket hacks to paste here:")
            j_txt = st.text_area("Paste JSON from chat:", height=260)
            if st.button("🚀 Import JSON") and j_txt:
                try:
                    np = json.loads(j_txt); np["id"] = int(datetime.now().timestamp())
                    data["places"].append(np); save_data(data); st.success("Imported!"); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# === PAGE 6: EXPENSES & SCHENGEN ===
elif page == "💸 Expenses & Schengen":
    c_ex, c_sc = st.columns(2)
    with c_ex:
        st.subheader("💸 Multi-Currency Expense Logger")
        if can_edit:
            with st.form("ex_f"):
                tr = st.text_input("Trip:", "Shaftesbury")
                it = st.text_input("Item (Coffee, Train, Flight):")
                am = st.number_input("Amount:", min_value=0.0, step=0.5)
                cu = st.selectbox("Currency:", ["GBP (£) x1.0", "EUR (€) x0.85", "PLN (zł) x0.20", "HUF (Ft) x0.0021"])
                if st.form_submit_button("➕ Log Expense") and it:
                    rate = {"GBP (£) x1.0":1.0, "EUR (€) x0.85":0.85, "PLN (zł) x0.20":0.20, "HUF (Ft) x0.0021":0.0021}[cu]
                    data["expenses"].append({"date":str(date.today()), "trip":tr, "item":it, "amount_gbp":round(am*rate,2), "category":"Travel"})
                    save_data(data); st.rerun()
        st.dataframe(data["expenses"], use_container_width=True)

    with c_sc:
        used_s, win_s = calc_schengen_rolling(data.get("schengen_trips", []))
        st.subheader(f"🛂 Schengen 90/180 Tracker ({90-used_s} Days Left)")
        st.caption(f"Rolling 180-day window from {win_s} to today: {used_s}/90 days used.")
        if can_edit:
            with st.form("sc_f"):
                sc_c = st.text_input("Country:")
                sc_s = st.date_input("Entry Date:", date.today())
                sc_e = st.date_input("Exit Date:", date.today()+timedelta(days=2))
                if st.form_submit_button("➕ Log Schengen Dates") and sc_c:
                    data["schengen_trips"].append({"country":sc_c, "start":str(sc_s), "end":str(sc_e)})
                    save_data(data); st.rerun()
        st.dataframe(data.get("schengen_trips", []), use_container_width=True)

# === PAGE 7: SETTINGS, OWNER LOCK & BACKUP ===
elif page == "⚙️ Settings, Lock & Backup":
    st.markdown("## ⚙️ Atlas Security Lock & Safe Backup")
    c_lk, c_bk = st.columns(2)
    with c_lk:
        st.subheader("🔑 Owner Password Lock (Visitor Read-Only Protection)")
        st.write("Set a PIN so if you share your public link with friends, they can view your map and photos but CANNOT edit or delete anything.")
        new_pin = st.text_input("Set or Change Owner PIN (leave blank to disable lock):", value=data.get("owner_pin",""), type="password")
        if st.button("💾 Save Security PIN"):
            data["owner_pin"] = new_pin; st.session_state.is_owner = True; save_data(data); st.success("Security updated!"); st.rerun()
    with c_bk:
        st.subheader("💾 Backup & Restore Data")
        st.download_button("📥 Download Full Atlas Backup (JSON)", data=json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"), file_name="smart_travel_atlas_backup.json", mime="application/json", use_container_width=True)
        up = st.file_uploader("📤 Restore from JSON Backup:", type=["json"])
        if up and can_edit and st.button("🔄 Confirm Restore"):
            data = json.load(up); save_data(data); st.success("Restored!"); st.rerun()
