import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os
import math
import requests
from datetime import datetime, time, timedelta, date

st.set_page_config(page_title="Smart Travel Atlas | Southampton", page_icon="🌿", layout="wide")

# === SECTION 1: PREMIUM VISUAL SYSTEM (CSS & THEME) ===
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap');

    /* Main Background & Typography */
    .stApp {
        background-color: #FAF8F5;
        color: #1F2421;
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3, .serif-title {
        font-family: 'Playfair Display', serif !important;
        color: #1B4332 !important;
        letter-spacing: -0.01em;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #F2EFE9 !important;
        border-right: 1px solid #E5E0D8;
    }

    /* Editorial Hero Banner */
    .hero-box {
        position: relative;
        border-radius: 18px;
        overflow: hidden;
        background-image: linear-gradient(180deg, rgba(20, 35, 28, 0.25) 0%, rgba(20, 35, 28, 0.78) 100%), 
                          url('https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=1600&q=85');
        background-size: cover;
        background-position: center;
        padding: 56px 44px;
        color: #FAF8F5;
        margin-bottom: 28px;
        box-shadow: 0 12px 30px rgba(27, 67, 50, 0.10);
    }
    .hero-tag {
        background: rgba(250, 248, 245, 0.2);
        backdrop-filter: blur(6px);
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        display: inline-block;
        margin-bottom: 14px;
    }
    .hero-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.7rem;
        font-weight: 700;
        color: #FFFFFF !important;
        margin: 0 0 10px 0;
        line-height: 1.15;
    }
    .hero-sub {
        font-size: 1.05rem;
        color: #E8ECE9;
        max-width: 620px;
        font-weight: 300;
        margin-bottom: 0;
    }

    /* Summary Stat Cards */
    .stat-card {
        background: #FFFFFF;
        border: 1px solid #EAE6DF;
        border-radius: 14px;
        padding: 20px 22px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.02);
        transition: transform 0.2s ease;
    }
    .stat-card:hover { transform: translateY(-2px); }
    .stat-label { font-size: 0.8rem; color: #6B756E; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
    .stat-val { font-size: 1.75rem; font-weight: 700; color: #1B4332; margin: 6px 0 2px 0; }
    .stat-sub { font-size: 0.82rem; color: #2D6A4F; }

    /* Destination Editorial Cards */
    .dest-card {
        background: #FFFFFF;
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid #EAE6DF;
        box-shadow: 0 6px 18px rgba(0,0,0,0.03);
        margin-bottom: 16px;
        transition: all 0.25s ease;
    }
    .dest-card:hover {
        box-shadow: 0 12px 26px rgba(27, 67, 50, 0.08);
        transform: translateY(-3px);
    }
    .dest-img {
        width: 100%;
        height: 200px;
        object-fit: cover;
    }
    .dest-body { padding: 18px 20px; }
    .badge-visited { background: #D8F3DC; color: #1B4332; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .badge-wishlist { background: #FFF3CD; color: #856404; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .badge-trust { background: #E6F2EF; color: #1F5E55; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; margin-left: 6px; }
</style>
""", unsafe_allow_html=True)

# === SECTION 2: DATA & HELPER FUNCTIONS ===
DATA_FILE = "travel_atlas_v4.json"
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
        except: pass
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
            "id": 4, "name": "Girona / Costa Brava (Extreme Day Trip)", "region": "Spain", "scope": "Europe",
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

@st.cache_data(ttl=86400)
def auto_lookup_place(query):
    out = {"ok": False, "lat": 50.9097, "lon": -1.4044, "dist": 50, "img": "", "summary": "", "name": query}
    try:
        headers = {"User-Agent": "SmartTravelAtlas/2.0"}
        r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": query, "format": "json", "limit": 1}, headers=headers, timeout=4).json()
        if r:
            out["lat"], out["lon"] = float(r[0]["lat"]), float(r[0]["lon"])
            out["dist"] = calc_distance_km(SOU_LAT, SOU_LON, out["lat"], out["lon"])
            out["ok"] = True
        clean_q = query.split(",")[0].strip().replace(" ", "_")
        w = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_q}", headers=headers, timeout=4).json()
        if "thumbnail" in w: out["img"] = w["thumbnail"]["source"]
        if "extract" in w: out["summary"] = w["extract"][:180] + "..."
    except: pass
    return out

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(DEFAULT_DATA, f, ensure_ascii=False, indent=2)
    with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)

data = load_data()

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
        "🇬🇧 UK Trips & Hikes",
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
    if c_top2.button("🇬🇧 Plan UK Trip", use_container_width=True): st.session_state.nav_page = "🇬🇧 UK Trips & Hikes"; st.rerun()
    if c_top3.button("✈️ Plan Europe / EDT", use_container_width=True): st.session_state.nav_page = "✈️ Europe, Airports & EDT"; st.rerun()

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

    cols = st.columns(3)
    for idx, p in enumerate(filtered_p):
        with cols[idx % 3]:
            b_cls = "badge-visited" if p["status"] == "visited" else "badge-wishlist"
            b_txt = "✓ Visited" if p["status"] == "visited" else "✦ Wishlist"
            img = p.get("image_url") or "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Durdle_Door_Overview.jpg/1024px-Durdle_Door_Overview.jpg"
            st.markdown(f"""
            <div class="dest-card">
                <img src="{img}" class="dest-img">
                <div class="dest-body">
                    <span class="{b_cls}">{b_txt}</span> <span class="badge-trust">{p.get('scope','UK')} • {p.get('community_tag','Nature')[:22]}</span>
                    <h4 style="margin:10px 0 4px 0;">{p['name']}</h4>
                    <div style="font-size:0.8rem; color:#6B756E; margin-bottom:8px;">📍 {p.get('region','')} • {p['distance_km']} km from SOU</div>
                    <div style="font-size:0.83rem; background:#F7F5F0; padding:8px; border-radius:8px; margin-bottom:8px;"><b>👀 Highlights:</b> {p.get('highlights','')[:75]}</div>
                    <div style="font-size:0.78rem; color:#854D0E;">🚨 <b>Curfew:</b> {p['last_return']} | 💳 {p['payment_rule'][:26]}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Open Details: {p['name'][:20]}", key=f"hb_{p['id']}", use_container_width=True):
                st.session_state.selected_place = p["name"]
                st.session_state.nav_page = "🇬🇧 UK Trips & Hikes" if p.get("scope","UK")=="UK" else "✈️ Europe, Airports & EDT"
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
    st_folium(m, width=1050, height=520)

# === PAGE 3: UK TRIPS & HIKES PLANNER ===
elif page == "🇬🇧 UK Trips & Hikes":
    st.markdown("## 🇬🇧 UK Day-Trips, National Trust Trails & Curfew Planner")
    uk_places = [p for p in data["places"] if p.get("scope", "UK") == "UK"]
    names = [p["name"] for p in uk_places]
    idx = names.index(st.session_state.get("selected_place")) if st.session_state.get("selected_place") in names else 0
    sel = st.selectbox("Select UK Destination:", names, index=idx)
    place = next(p for p in data["places"] if p["name"] == sel)

    col_l, col_r = st.columns([1.05, 1.45])
    with col_l:
        st.image(place.get("image_url"), use_container_width=True)
        if can_edit and st.button("🔄 Toggle Visited / Wishlist Status", use_container_width=True):
            place["status"] = "visited" if place["status"] != "visited" else "wishlist"; save_data(data); st.rerun()
        st.info(f"🏛️ **Trust / Community:** {place.get('community_tag','')}\n\n👀 **What You'll See:** {place.get('highlights','')}\n\n📝 **Notes:** {place.get('notes','')}")
        
        q_clean = place["name"].split("(")[0].strip().replace(" ", "+")
        b1, b2, b3 = st.columns(3)
        b1.link_button("🚆 Google Transit", f"https://www.google.com/maps/dir/Southampton+Central/{q_clean}/", use_container_width=True)
        if "Hike" in place["category"] or "Walk" in place["category"] or place.get("source_link"):
            b2.link_button("🥾 Trail / Source", place.get("source_link") or f"https://www.alltrails.com/search?q={q_clean}", use_container_width=True)
        b3.link_button("🏛️ National Trust", f"https://www.google.com/search?q={q_clean}+national+trust+english+heritage", use_container_width=True)

    with col_r:
        w = get_live_weather_and_sunset(place["lat"], place["lon"])
        if w.get("ok"):
            w1, w2, w3 = st.columns(3)
            w1.metric("🌡️ Live Temp", f"{w['temp']}°C"); w2.metric("🌧️ Rain Prob", f"{w['rain_prob']}%"); w3.metric("🌅 Sunset Today", w["sunset"])

        st.markdown("#### ⏱️ Reverse Timeline & Last-Bus Curfew Calculator")
        tc1, tc2, tc3, tc4 = st.columns(4)
        dep_t = tc1.time_input("Leave SOU:", datetime.strptime(place.get("dep_time","08:30"),"%H:%M").time())
        tr_m = tc2.number_input("Train/Bus (m):", value=int(place.get("transit_mins",90)), step=5)
        ac_h = tc3.number_input("Walk/Stay (h):", value=float(place.get("activity_hours",4.0)), step=0.5)
        lr_t = tc4.time_input("🚨 Last Return:", datetime.strptime(place.get("last_return","18:00"),"%H:%M").time())

        arr_dt = datetime.combine(date.today(), dep_t) + timedelta(minutes=tr_m)
        fin_dt = arr_dt + timedelta(hours=ac_h)
        buf_m = int((datetime.combine(date.today(), lr_t) - fin_dt).total_seconds() / 60)
        st.write(f"**Arrive:** `{arr_dt.strftime('%H:%M')}` ➡️ **Finish Walk:** `{fin_dt.strftime('%H:%M')}` ➡️ **Last Bus/Train:** `{lr_t.strftime('%H:%M')}`")
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
            with st.expander("✏️ Edit Trip Details, Photo & Prices"):
                place["image_url"] = st.text_input("Image URL:", place.get("image_url",""))
                place["highlights"] = st.text_input("What You'll See (Highlights):", place.get("highlights",""))
                place["last_transit_note"] = st.text_input("Last Bus/Train Note:", place.get("last_transit_note",""))
                place["payment_rule"] = st.text_input("Payment Rule:", place.get("payment_rule",""))
                place["paid_gbp"] = st.number_input("Paid (£):", value=float(place.get("paid_gbp",0.0)))
                place["saved_gbp"] = st.number_input("Saved (£):", value=float(place.get("saved_gbp",0.0)))
                if st.button("💾 Save UK Trip Changes"):
                    place["dep_time"], place["transit_mins"], place["activity_hours"], place["last_return"] = dep_t.strftime("%H:%M"), tr_m, ac_h, lr_t.strftime("%H:%M")
                    save_data(data); st.success("Saved!"); st.rerun()

# === PAGE 4: EUROPE, DYNAMIC AIRPORTS & EXTREME DAY TRIPS (EDT) ===
elif page == "✈️ Europe, Airports & EDT":
    st.markdown("## ✈️ Europe Escapes, Custom Airport Matrix & Extreme Day Trips")
    
    # 1. Extreme Day Trip (EDT) Radar
    st.markdown("### ⚡ 1. Spontaneous 'Extreme Day Trip' (EDT) Cheap Flight Hunter")
    st.caption("Want to fly to Spain, Italy, or Poland for £15–£25, explore a new city for a full day, and sleep back in your bed? Check live 'Everywhere' deals from airports near Southampton:")
    e1, e2, e3, e4 = st.columns(4)
    e1.link_button("🔥 From Bournemouth (BOH)", "https://www.skyscanner.net/transport/flights-from/boh/", use_container_width=True)
    e2.link_button("⭐ From Bristol (BRS)", "https://www.skyscanner.net/transport/flights-from/brs/", use_container_width=True)
    e3.link_button("✈️ From Gatwick (LGW)", "https://www.skyscanner.net/transport/flights-from/lgw/", use_container_width=True)
    e4.link_button("🎒 Ryanair Cheap Finder", "https://www.ryanair.com/gb/en/cheap-flights", use_container_width=True)

    st.divider()
    # 2. Custom Per-City Door-to-Door Airport Calculator
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
    st.success(f"🏆 **Cheapest Door-to-Door Route to {target_city}: {win['UK Airport']}** — Total: **£{win['REAL DOOR-TO-DOOR TOTAL (£)']:.2f}** (includes Southampton train/bus + flight + Europe city transfer!)")
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
            st.subheader("🔍 1. Auto-Fetch Place (Wikipedia + Map + Any Social Link)")
            st.caption("Type ANY village, hike, or obscure European city! It auto-fetches coordinates, distance from Southampton, and Wikipedia photo.")
            q_search = st.text_input("Place or City Name:", placeholder="e.g., Zaragoza, Spain OR Corfe Castle, UK")
            if "lookup" not in st.session_state: st.session_state.lookup = {"name":"", "lat":50.9097, "lon":-1.4044, "dist":50, "img":"", "summary":""}
            if st.button("🔍 Auto-Fetch Details & Photo") and q_search:
                res = auto_lookup_place(q_search)
                st.session_state.lookup = res
                if res["ok"]: st.success(f"Found! {res['dist']} km from Southampton.")
                else: st.warning("Coordinates not exact—you can still save or adjust below.")

            with st.form("add_uni_form"):
                lk = st.session_state.lookup
                f_name = st.text_input("Title:", value=lk.get("name") or q_search)
                f_scope = st.selectbox("Trip Scope:", ["UK", "Europe"])
                f_cat = st.selectbox("Category:", ["Historic Village", "Linear Hike / Nature", "Coastal Walk", "Extreme Day Trip (EDT)", "European City Break", "Food & Cafe Spot"])
                f_trust = st.text_input("Community / Trust / Airline Tag:", "National Trust / Ryanair EDT")
                f_link = st.text_input("🔗 Source Link (Instagram, TikTok, AllTrails, Google Maps, Blog):", placeholder="Paste any link where you discovered this spot...")
                f_high = st.text_area("👀 What You'll See (Highlights):", value=lk.get("summary",""))
                f_img = st.text_input("Photo URL (Auto-filled from Wikipedia if available):", value=lk.get("img",""))
                c1, c2 = st.columns(2)
                f_last = c1.text_input("🚨 Last Return Bus/Train/Flight:", "19:30")
                f_pay = c2.text_input("💳 Local Payment Rule:", "Contactless OK")
                
                if st.form_submit_button("📌 Save Destination to My Atlas"):
                    if f_name:
                        data["places"].append({
                            "id": len(data["places"])+1, "name": f_name, "region": f_scope, "scope": f_scope,
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
            j_txt = st.text_area("Paste JSON from chat:", height=260)
            if st.button("🚀 Import JSON") and j_txt:
                try:
                    np = json.loads(j_txt); np["id"] = len(data["places"])+1
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
