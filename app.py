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
    "places": [
        {
            "id": 1,
            "name": "Durdle Door & Lulworth Cove",
            "region": "Dorset, England",
            "scope": "UK",
            "category": "Coastal Walk",
            "community_tag": "Jurassic Coast Trust / SW Coast Path",
            "status": "wishlist",
            "lat": 50.6212, "lon": -2.2768, "distance_km": 69, "rating": 5,
            "paid_gbp": 16.20, "saved_gbp": 8.50,
            "saving_hack": "SWR Railcard Return to Wool + £2 Morebus Cap",
            "dep_time": "09:00", "transit_mins": 85, "activity_hours": 4.0, "last_return": "17:15",
            "last_transit_note": "Morebus 30 to Wool Station ends early in autumn/winter!",
            "payment_rule": "Contactless OK (Remember to Tap Off on exit!)",
            "ticket_info": "Free access (Lulworth Estate car park paid, bus free entry)",
            "highlights": "Limestone sea arch, Stair Hole folded rocks, Lulworth village cottages",
            "notes": "Direct train from Southampton Central to Wool, then scenic double-decker bus.",
            "image_url": "https://images.unsplash.com/photo-1544644181-1484b3fdfc62?auto=format&fit=crop&w=900&q=80",
            "checkpoints": [
                {"task": "Direct train from Southampton Central to Wool Station", "done": False},
                {"task": "Morebus 30 from Wool Station to Durdle Door", "done": False},
                {"task": "Walk chalk cliff path to Lulworth Cove", "done": False}
            ]
        },
        {
            "id": 2,
            "name": "South Downs Way (Hassocks to Lewes)",
            "region": "East Sussex, England",
            "scope": "UK",
            "category": "Linear Ridge Hike (17 km)",
            "community_tag": "National Trust (Ditchling Beacon) / Ramblers",
            "status": "wishlist",
            "lat": 50.9086, "lon": -0.1072, "distance_km": 92, "rating": 5,
            "paid_gbp": 20.70, "saved_gbp": 18.00,
            "saving_hack": "Off-Peak Return to Lewes + short Single (Brighton-Hassocks)",
            "dep_time": "08:30", "transit_mins": 132, "activity_hours": 4.5, "last_return": "21:02",
            "last_transit_note": "Watch sunset on the ridge! Last direct Brighton->Southampton train at 21:02",
            "payment_rule": "Railcard on App | Emergency Breeze Bus 79 at Ditchling Beacon (£2 Card)",
            "ticket_info": "Free National Trail - Bring 2L water (no shops on ridge)",
            "highlights": "Jack & Jill Windmills, Ditchling Beacon 360° summit, Historic Lewes Castle",
            "notes": "Linear station-to-station hike across rolling chalk hills.",
            "image_url": "https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=900&q=80",
            "checkpoints": [
                {"task": "08:30 Southern train to Hassocks (Platform 2 exit)", "done": False},
                {"task": "Climb to Jack and Jill Windmills", "done": False},
                {"task": "Summit Ditchling Beacon (National Trust viewpoint)", "done": False},
                {"task": "Descend to Lewes for coffee & return train via Brighton", "done": False}
            ]
        },
        {
            "id": 3,
            "name": "Shaftesbury & Gold Hill",
            "region": "Dorset, England",
            "scope": "UK",
            "category": "Historic Hilltop Town",
            "community_tag": "English Heritage (Shaftesbury Abbey) / Dorset AONB",
            "status": "visited",
            "lat": 51.0045, "lon": -2.1983, "distance_km": 68, "rating": 5,
            "paid_gbp": 14.50, "saved_gbp": 12.00,
            "saving_hack": "Railcard 1/3 off to Gillingham + £2 Bus Cap",
            "dep_time": "09:30", "transit_mins": 95, "activity_hours": 3.5, "last_return": "17:38",
            "last_transit_note": "Last bus (X2/B3) from Shaftesbury to Gillingham Station is at 17:38!",
            "payment_rule": "Contactless / Apple Pay accepted on local bus",
            "ticket_info": "Gold Hill street & Park Walk viewpoint are free 24/7",
            "highlights": "Famous cobbled Gold Hill, Blackmore Vale views, Abbey ruins",
            "notes": "A peaceful rural escape. Alighted at Gillingham station then took the local bus.",
            "image_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=900&q=80",
            "checkpoints": [
                {"task": "Train from Southampton to Gillingham (Dorset)", "done": True},
                {"task": "Local bus to Shaftesbury town centre", "done": True},
                {"task": "Walk Gold Hill & catch 17:38 bus back", "done": True}
            ]
        }
    ],
    "expenses": [
        {"date": "2026-10-16", "trip": "Shaftesbury", "item": "Train to Gillingham", "amount_gbp": 10.50, "category": "Transit"},
        {"date": "2026-10-16", "trip": "Shaftesbury", "item": "Return Bus X2", "amount_gbp": 4.00, "category": "Transit"},
        {"date": "2026-10-16", "trip": "Shaftesbury", "item": "Coffee & Pastry", "amount_gbp": 5.20, "category": "Food & Coffee"}
    ],
    "schengen_trips": [
        {"country": "Italy (Milan & Como)", "start": "2026-06-10", "end": "2026-06-16"},
        {"country": "Poland (Krakow)", "start": "2026-08-20", "end": "2026-08-24"}
    ]
}

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_DATA, f, ensure_ascii=False, indent=4)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=4)

data = load_data()

# === SECTION 3: CLEAN SIDEBAR NAVIGATION ===
with st.sidebar:
    st.markdown("## 🌿 Smart Travel Atlas")
    st.caption("Your journeys from Southampton, thoughtfully planned.")
    st.divider()
    
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = "🏡 Home & Inspiration"
        
    nav_options = [
        "🏡 Home & Inspiration",
        "🗺️ Explore & Pin Map",
        "🇬🇧 UK Trips & Hikes Planner",
        "✈️ Europe, Airports & EDT",
        "💸 Expenses & Schengen",
        "⚙️ Settings & Backup"
    ]
    page = st.radio("Navigation", nav_options, index=nav_options.index(st.session_state.nav_page) if st.session_state.nav_page in nav_options else 0)
    st.session_state.nav_page = page
    
    st.divider()
    st.caption("🌱 **Quick Tip:** Use 'UK Trips' for rural bus/train curfews & National Trust trails, and 'Europe' for extreme day trips & airport comparisons.")

# === SECTION 4: PAGE 1 - HOME & EDITORIAL DASHBOARD ===
if page == "🏡 Home & Inspiration":
    # A. Top Editorial Header
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown("### 🌿 Smart Travel Planner & Memory Atlas")
    with h_col2:
        if st.button("➕ Plan New Journey", use_container_width=True):
            st.session_state.nav_page = "🇬🇧 UK Trips & Hikes Planner"
            st.rerun()

    # B. Hero Section (British Countryside & Coast Inspiration)
    st.markdown("""
    <div class="hero-box">
        <div class="hero-tag">⚓ Base Hub: Southampton, UK</div>
        <div class="hero-title">The British countryside & Europe are waiting.</div>
        <p class="hero-sub">Plan scenic railway hikes, discover National Trust coastlines, compare door-to-door flights, and preserve every memory on your personal atlas.</p>
    </div>
    """, unsafe_allow_html=True)

    # C. Personal Travel Summary (Clean Editorial Cards)
    visited_list = [p for p in data["places"] if p["status"] == "visited"]
    wishlist_list = [p for p in data["places"] if p["status"] != "visited"]
    total_spent = sum(e.get("amount_gbp", 0) for e in data["expenses"])
    total_km = sum(p.get("distance_km", 0) * 2 for p in visited_list)
    used_sch, _ = calc_schengen_rolling(data.get("schengen_trips", []))

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"""<div class="stat-card"><div class="stat-label">Places Explored</div><div class="stat-val">{len(visited_list)} Visited</div><div class="stat-sub">{len(wishlist_list)} saved in Wishlist</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="stat-card"><div class="stat-label">Journey Distance</div><div class="stat-val">{total_km} km</div><div class="stat-sub">Round-trip from Southampton</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="stat-card"><div class="stat-label">Recorded Expenses</div><div class="stat-val">£{total_spent:.2f}</div><div class="stat-sub">Verified smart rail & bus logs</div></div>""", unsafe_allow_html=True)
    c4.markdown(f"""<div class="stat-card"><div class="stat-label">Schengen Window</div><div class="stat-val">{90 - used_sch} Days Left</div><div class="stat-sub">{used_sch}/90 used in rolling 180d</div></div>""", unsafe_allow_html=True)

    st.write("")
    st.write("")

    # D. Your Next Adventure (Visual Destination Cards with Nature/Heritage Highlights)
    st.markdown("## 🧭 Your Next Adventure & Saved Escapes")
    st.caption("Curated trails, coastal walks, and historic villages with verified transit curfews and community highlights.")

    cols = st.columns(3)
    for idx, p in enumerate(data["places"]):
        with cols[idx % 3]:
            badge_cls = "badge-visited" if p["status"] == "visited" else "badge-wishlist"
            badge_txt = "✓ Visited" if p["status"] == "visited" else "✦ Wishlist"
            trust_tag = p.get("community_tag", "Nature & Heritage")
            img = p.get("image_url") or "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80"
            
            st.markdown(f"""
            <div class="dest-card">
                <img src="{img}" class="dest-img" alt="{p['name']}">
                <div class="dest-body">
                    <span class="{badge_cls}">{badge_txt}</span>
                    <span class="badge-trust">🏛️ {trust_tag.split('/')[0]}</span>
                    <h4 style="margin:12px 0 4px 0; color:#1B4332; font-family:'Playfair Display',serif;">{p['name']}</h4>
                    <div style="font-size:0.82rem; color:#6B756E; margin-bottom:10px;">📍 {p.get('region', 'UK')} • {p['distance_km']} km from SOU</div>
                    <div style="font-size:0.85rem; color:#2D3A32; background:#F7F5F0; padding:8px 10px; border-radius:8px; margin-bottom:10px;">
                        <b>👀 What you'll see:</b> {p.get('highlights', p.get('notes', '')[:70])}
                    </div>
                    <div style="font-size:0.8rem; color:#854D0E;">🚨 <b>Curfew:</b> {p['last_return']} ({p['payment_rule'][:28]}...)</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Open Trip Planner: {p['name'][:18]}...", key=f"home_btn_{p['id']}", use_container_width=True):
                st.session_state.selected_place = p["name"]
                st.session_state.nav_page = "🇬🇧 UK Trips & Hikes Planner"
                st.rerun()

    st.divider()

    # E. My Travel Atlas Preview
    map_c1, map_c2 = st.columns([2.2, 1])
    with map_c1:
        st.markdown("### 🗺️ My Travel Atlas Preview")
        m = folium.Map(location=[SOU_LAT, SOU_LON], zoom_start=8)
        folium.Marker([SOU_LAT, SOU_LON], tooltip="🏠 Southampton Base Hub", icon=folium.Icon(color="black", icon="home")).add_to(m)
        for p in data["places"]:
            col = "green" if p["status"] == "visited" else "orange"
            folium.Marker([p["lat"], p["lon"]], tooltip=f"{p['name']} ({p.get('community_tag', '')})", icon=folium.Icon(color=col, icon="leaf")).add_to(m)
        st_folium(m, width=720, height=340)
    with map_c2:
        st.markdown("### 🌲 British Nature & Heritage")
        st.write("Every pin in your atlas records:")
        st.markdown("""
        - **🏛️ Trust & Community Insights:** Know whether a spot belongs to *National Trust*, *English Heritage*, or *National Trails*.
        - **👀 On-Route Highlights:** See what landmarks, windmills, or coastal arches lie along your path.
        - **🚌 Rural Transit Survival:** Exact last-bus curfews and local payment rules (Cash vs. Contactless).
        """)
        if st.button("🗺️ Open Full Interactive Map", use_container_width=True):
            st.session_state.nav_page = "🗺️ Explore & Pin Map"
            st.rerun()

# === SECTION 5: OTHER PAGES (READY FOR STEP 2 & 3 UPGRADES) ===
elif page == "🗺️ Explore & Pin Map":
    st.markdown("## 🗺️ Full Interactive Memory & Wishlist Map")
    f_col = st.radio("Filter Pins:", ["All Places", "Visited Only (Green)", "Wishlist Only (Amber)"], horizontal=True)
    m = folium.Map(location=[SOU_LAT, SOU_LON], zoom_start=7)
    folium.Marker([SOU_LAT, SOU_LON], tooltip="Southampton Hub", icon=folium.Icon(color="black", icon="home")).add_to(m)
    for p in data["places"]:
        if f_col == "Visited Only (Green)" and p["status"] != "visited": continue
        if f_col == "Wishlist Only (Amber)" and p["status"] == "visited": continue
        col = "green" if p["status"] == "visited" else "orange"
        folium.Marker([p["lat"], p["lon"]], popup=f"<b>{p['name']}</b><br>Last Return: {p['last_return']}", tooltip=p["name"], icon=folium.Icon(color=col)).add_to(m)
    st_folium(m, width=1050, height=540)

elif page == "🇬🇧 UK Trips & Hikes Planner":
    st.markdown("## 🇬🇧 UK Day-Trips, Hikes & Curfew Planner")
    names = [p["name"] for p in data["places"]]
    default_idx = names.index(st.session_state.get("selected_place")) if st.session_state.get("selected_place") in names else 0
    sel = st.selectbox("Choose a UK Destination:", names, index=default_idx)
    place = next(p for p in data["places"] if p["name"] == sel)
    
    c_img, c_info = st.columns([1.1, 1.4])
    with c_img:
        st.image(place.get("image_url"), use_container_width=True)
        st.info(f"🏛️ **Community / Trust:** {place.get('community_tag', 'UK Countryside')}\n\n👀 **What you'll see:** {place.get('highlights', '')}")
    with c_info:
        st.markdown(f"### {place['name']} ({place.get('region', 'UK')})")
        w = get_live_weather_and_sunset(place["lat"], place["lon"])
        if w.get("ok"):
            w1, w2, w3 = st.columns(3)
            w1.metric("🌡️ Current Temp", f"{w['temp']}°C")
            w2.metric("🌧️ Rain Chance", f"{w['rain_prob']}%")
            w3.metric("🌅 Sunset Today", w["sunset"])
        st.error(f"🚨 **Last Return Curfew:** {place['last_return']} — {place['last_transit_note']}")
        st.warning(f"💳 **Local Bus/Train Payment:** {place['payment_rule']}")
        st.success(f"💡 **Ticketing Hack:** {place['saving_hack']} (Saved £{place['saved_gbp']})")
        st.markdown("#### ☑️ Route Checkpoints")
        for i, cp in enumerate(place.get("checkpoints", [])):
            st.checkbox(cp["task"], value=cp["done"], key=f"uk_cp_{i}")

elif page == "✈️ Europe, Airports & EDT":
    st.markdown("## ✈️ Europe Planner, Dynamic Airport Matrix & Extreme Day Trips")
    st.info("🔜 Step 2 Upgrade will expand this section with custom per-trip airport comparisons and the Extreme Day-Trip (EDT) cheap flight radar!")

elif page == "💸 Expenses & Schengen":
    st.markdown("## 💸 Expense Tracker & Rolling 180-Day Schengen Calculator")
    used_s, win_s = calc_schengen_rolling(data.get("schengen_trips", []))
    st.metric("Schengen Days Remaining (90/180 Rule)", f"{90 - used_s} Days Left", f"Used {used_s} days since {win_s}")
    st.dataframe(data["expenses"], use_container_width=True)

elif page == "⚙️ Settings & Backup":
    st.markdown("## ⚙️ Settings & Safe Data Backup")
    st.write("Export your entire atlas (places, notes, checkpoints, expenses, and Schengen logs) as a portable JSON file.")
    st.download_button("💾 Download Full Atlas Backup", data=json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"), file_name="atlas_backup.json", mime="application/json")
