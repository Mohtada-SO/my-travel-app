import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os
import math
import requests
from datetime import datetime, time, timedelta, date

st.set_page_config(page_title="Southampton & Europe Travel Atlas", page_icon="🌍", layout="wide")

DATA_FILE = "travel_atlas_v3.json"
SOU_LAT, SOU_LON = 50.9097, -1.4044

# --- Helper Functions (Haversine, Live Weather, Auto-Geocoder) ---
def calc_distance_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return round(R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))))

@st.cache_data(ttl=1800)
def get_live_weather_and_sunset(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m,precipitation&daily=sunset,precipitation_probability_max&timezone=auto"
        r = requests.get(url, timeout=4).json()
        temp = r["current"]["temperature_2m"]
        wind = r["current"]["wind_speed_10m"]
        rain_prob = r["daily"]["precipitation_probability_max"][0]
        sunset_iso = r["daily"]["sunset"][0]
        sunset_time = sunset_iso.split("T")[1] if "T" in sunset_iso else "18:00"
        return {"temp": temp, "wind": wind, "rain_prob": rain_prob, "sunset": sunset_time, "ok": True}
    except:
        return {"ok": False}

@st.cache_data(ttl=86400)
def geocode_place(query):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "SouthamptonStudentTravelAtlas/1.0"}
        r = requests.get(url, params={"q": query, "format": "json", "limit": 1}, headers=headers, timeout=5).json()
        if r:
            lat, lon = float(r[0]["lat"]), float(r[0]["lon"])
            dist = calc_distance_km(SOU_LAT, SOU_LON, lat, lon)
            return {"lat": lat, "lon": lon, "dist": dist, "display_name": r[0]["display_name"], "ok": True}
    except:
        pass
    return {"ok": False}

def calc_schengen_rolling(trips, ref_date=None):
    if ref_date is None:
        ref_date = date.today()
    window_start = ref_date - timedelta(days=179)
    used_days = set()
    for t in trips:
        try:
            s = datetime.strptime(t["start"], "%Y-%m-%d").date()
            e = datetime.strptime(t["end"], "%Y-%m-%d").date()
            curr = s
            while curr <= e:
                if window_start <= curr <= ref_date:
                    used_days.add(curr)
                curr += timedelta(days=1)
        except:
            pass
    return len(used_days), window_start

DEFAULT_DATA = {
    "places": [
        {
            "id": 1,
            "name": "Shaftesbury (Gold Hill)",
            "country": "UK",
            "category": "Historic Village",
            "status": "visited",
            "lat": 51.0045,
            "lon": -2.1983,
            "distance_km": 68,
            "rating": 5,
            "paid_gbp": 14.50,
            "saved_gbp": 12.00,
            "saving_hack": "Railcard 1/3 off + £2 Bus Cap",
            "dep_time": "09:30",
            "transit_mins": 95,
            "activity_hours": 3.5,
            "last_return": "17:38",
            "last_transit_note": "Last bus (X2/B3) to Gillingham Station at 17:38!",
            "payment_rule": "🟢 Contactless / Apple Pay accepted on bus",
            "ticket_info": "🆓 Free entry 24/7 to Gold Hill",
            "mood": "😌 Peaceful rural vibes",
            "notes": "Train to Gillingham (Dorset) then local bus. Buses run roughly every hour, so watch the return clock closely.",
            "image_url": "https://images.unsplash.com/photo-1590001155093-a3c66ab0c3ff?auto=format&fit=crop&w=800&q=80",
            "checkpoints": [
                {"task": "Train from Southampton Central to Gillingham", "done": True},
                {"task": "Catch Bus X2/B3 outside station to Shaftesbury", "done": True},
                {"task": "Walk iconic Gold Hill cobbled street & viewpoint", "done": True},
                {"task": "Catch 17:38 return bus back to Gillingham", "done": True}
            ]
        },
        {
            "id": 2,
            "name": "South Downs Hike (Hassocks to Lewes)",
            "country": "UK",
            "category": "Linear Hike (17 km)",
            "status": "wishlist",
            "lat": 50.9086,
            "lon": -0.1072,
            "distance_km": 92,
            "rating": 5,
            "paid_gbp": 20.70,
            "saved_gbp": 18.00,
            "saving_hack": "Off-Peak Day Return to Lewes + short Single (Brighton-Hassocks)",
            "dep_time": "08:30",
            "transit_mins": 132,
            "activity_hours": 4.5,
            "last_return": "21:02",
            "last_transit_note": "🚨 Watch sunset time! Last direct Brighton->Southampton train at 21:02",
            "payment_rule": "🟢 Use Railcard on App | Emergency Breeze Bus 79 at Ditchling Beacon (£2 Apple Pay)",
            "ticket_info": "🆓 Free trail - ⚠️ NO water/shops along the 17km ridge!",
            "mood": "🤩 Excited for the ridge views",
            "notes": "Exit Hassocks Platform 2 -> Jack & Jill Windmills -> Ditchling Beacon (248m peak) -> Descend into Lewes town.",
            "image_url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80",
            "checkpoints": [
                {"task": "Pack 2L water, lunch & waterproof jacket in Southampton", "done": False},
                {"task": "08:30 Southern train (change at Angmering/Brighton) to Hassocks", "done": False},
                {"task": "Climb up to Jack and Jill Windmills", "done": False},
                {"task": "Lunch break at Ditchling Beacon 360° viewpoint", "done": False},
                {"task": "Finish hike in Lewes, grab coffee & take 15-min train to Brighton", "done": False}
            ]
        },
        {
            "id": 3,
            "name": "Durdle Door & Lulworth Cove",
            "country": "UK",
            "category": "Coastal Walk",
            "status": "wishlist",
            "lat": 50.6212,
            "lon": -2.2768,
            "distance_km": 69,
            "rating": 5,
            "paid_gbp": 16.20,
            "saved_gbp": 8.50,
            "saving_hack": "SWR Railcard Return to Wool + £2 Morebus Cap",
            "dep_time": "09:00",
            "transit_mins": 85,
            "activity_hours": 4.0,
            "last_return": "17:15",
            "last_transit_note": "Morebus 30 to Wool Station ends early in autumn/winter!",
            "payment_rule": "🟢 Contactless OK (Remember to Tap Off when exiting the bus!)",
            "ticket_info": "🆓 Free beach & coastal path access",
            "mood": "🌊 Coastal adventure",
            "notes": "Best visited on a clear sunny day before sunset.",
            "image_url": "https://images.unsplash.com/photo-1544644181-1484b3fdfc62?auto=format&fit=crop&w=800&q=80",
            "checkpoints": [
                {"task": "Direct train from Southampton Central to Wool Station", "done": False},
                {"task": "Take Morebus 30 from Wool Station to Durdle Door", "done": False},
                {"task": "Walk the cliff path from Durdle Door to Lulworth Cove", "done": False}
            ]
        }
    ],
    "expenses": [
        {"date": "2026-10-16", "trip": "Shaftesbury", "item": "Train to Gillingham", "amount_gbp": 10.50, "category": "Transit 🚆"},
        {"date": "2026-10-16", "trip": "Shaftesbury", "item": "Return Bus X2", "amount_gbp": 4.00, "category": "Transit 🚌"},
        {"date": "2026-10-16", "trip": "Shaftesbury", "item": "Coffee & Pastry", "amount_gbp": 5.20, "category": "Food & Coffee ☕"}
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

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data = load_data()

# ----------------- Sidebar: 1-Click Backup & Restore -----------------
with st.sidebar:
    st.header("⚙️ Atlas Controls & Backup")
    st.caption("Download your data anytime so your memories are 100% safe.")
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button("💾 Download Full Backup (JSON)", data=json_bytes, file_name="my_travel_backup.json", mime="application/json")
    
    uploaded_backup = st.file_uploader("📂 Restore from Backup", type=["json"])
    if uploaded_backup is not None:
        if st.button("🔄 Restore Data Now"):
            data = json.load(uploaded_backup)
            save_data(data)
            st.success("Backup restored!")
            st.rerun()

# ----------------- Top Metrics Dashboard -----------------
st.title("🌍 Smart Travel Planner & Memory Atlas")
st.caption("Base Hub: Southampton, UK ⚓ | Live Weather, Curfew Calculator, Airport Matrix & Schengen Tracker")

visited_places = [p for p in data["places"] if p["status"] == "visited"]
total_km = sum(p.get("distance_km", 0) * 2 for p in visited_places)
total_paid = sum(e.get("amount_gbp", 0) for e in data["expenses"])
total_saved = sum(p.get("saved_gbp", 0) for p in data["places"])
used_schengen, win_start = calc_schengen_rolling(data.get("schengen_trips", []))
schengen_left = max(0, 90 - used_schengen)

m1, m2, m3, m4 = st.columns(4)
m1.metric("📍 Visited / Total Pins", f"{len(visited_places)} / {len(data['places'])}", "From Southampton Hub")
m2.metric("💰 Total Spent", f"£{total_paid:.2f}", f"Smart Saved: £{total_saved:.2f} 🔥")
m3.metric("📏 Distance Covered", f"{total_km} km", "Round-trip from SOU")
m4.metric("🛂 Schengen (Rolling 180d)", f"{schengen_left} Days Left", f"{used_schengen}/90 used since {win_start}")

st.divider()

# ----------------- Main Navigation Tabs -----------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Map, Live Weather & Planner", 
    "✈️ UK Airport Matrix", 
    "💸 Expense Tracker", 
    "🛂 Schengen 90/180 Tracker",
    "➕ Smart Auto-Add / AI Import"
])

# === TAB 1: Map, Live Weather & Interactive Planner ===
with tab1:
    col_map, col_plan = st.columns([1.15, 1.35])
    
    with col_map:
        st.subheader("📍 Interactive Pin Map")
        f_status = st.radio("Filter Map Pins:", ["All Pins", "🟢 Visited Only", "🟡 Wishlist Only"], horizontal=True)
        
        m = folium.Map(location=[SOU_LAT, SOU_LON], zoom_start=8)
        folium.Marker(
            [SOU_LAT, SOU_LON],
            popup="🏠 Southampton Base Hub",
            tooltip="🏠 Southampton (Home Base)",
            icon=folium.Icon(color="black", icon="home")
        ).add_to(m)

        for p in data["places"]:
            if f_status == "🟢 Visited Only" and p["status"] != "visited":
                continue
            if f_status == "🟡 Wishlist Only" and p["status"] == "visited":
                continue
            color = "green" if p["status"] == "visited" else ("orange" if p["status"] == "food" else "blue")
            status_tag = "VISITED" if p["status"] == "visited" else "WISHLIST"
            stars = "⭐" * int(p.get("rating", 5))
            popup_html = f"""
            <div style="font-family:sans-serif; width:210px;">
                <b>{p['name']}</b> <span style="color:gray;">({status_tag})</span><br>
                <span>{stars}</span> | <small>{p['distance_km']} km from SOU</small><hr style="margin:5px 0;">
                🚨 <b>Last Return:</b> {p['last_return']}<br>
                💳 <b>Pay:</b> {p['payment_rule']}<br>
                💰 <b>Saved:</b> £{p.get('saved_gbp', 0)}
            </div>
            """
            folium.Marker(
                [p["lat"], p["lon"]],
                popup=folium.Popup(popup_html, max_width=240),
                tooltip=f"{p['name']} ({status_tag})",
                icon=folium.Icon(color=color, icon="info-sign")
            ).add_to(m)
            
        st_folium(m, width=580, height=520)

    with col_plan:
        place_names = [p["name"] for p in data["places"]]
        selected_name = st.selectbox("🎯 Select Destination to Plan, Check Live Weather or Edit:", place_names)
        p_idx = next(i for i, p in enumerate(data["places"]) if p["name"] == selected_name)
        place = data["places"][p_idx]
        
        # Header + Status Toggle
        sc1, sc2 = st.columns([2.2, 1])
        badge = "🟢 VISITED" if place["status"] == "visited" else "🟡 WISHLIST"
        stars_str = "⭐" * int(place.get("rating", 5))
        sc1.markdown(f"### {place['name']} `{badge}` {stars_str}")
        if sc2.button("🔄 Toggle Visited / Wishlist"):
            place["status"] = "visited" if place["status"] != "visited" else "wishlist"
            save_data(data)
            st.rerun()

        # --- LIVE WEATHER & SUNSET RADAR ---
        weather = get_live_weather_and_sunset(place["lat"], place["lon"])
        if weather.get("ok"):
            wc1, wc2, wc3, wc4 = st.columns(4)
            wc1.metric("🌡️ Live Temp", f"{weather['temp']} °C")
            wc2.metric("💨 Wind Speed", f"{weather['wind']} km/h")
            wc3.metric("🌧️ Rain Chance", f"{weather['rain_prob']}%")
            wc4.metric("🌅 Sunset Today", f"{weather['sunset']}")
            if st.button(f"🌅 Set Curfew to Sunset ({weather['sunset']})"):
                place["last_return"] = weather["sunset"]
                save_data(data)
                st.rerun()

        # --- LIVE REVERSE TIMELINE CALCULATOR ---
        st.markdown("#### ⏱️ 1. Live Day-Trip Timeline & Curfew Calculator")
        tc1, tc2, tc3, tc4 = st.columns(4)
        try:
            default_dep = datetime.strptime(place.get("dep_time", "08:30"), "%H:%M").time()
            default_last = datetime.strptime(place.get("last_return", "18:00"), "%H:%M").time()
        except:
            default_dep, default_last = time(8, 30), time(18, 0)

        dep_t = tc1.time_input("Leave SOU:", value=default_dep, key=f"dep_{p_idx}")
        trans_m = tc2.number_input("Transit (m):", value=int(place.get("transit_mins", 90)), step=5, key=f"tr_{p_idx}")
        act_h = tc3.number_input("Activity (h):", value=float(place.get("activity_hours", 4.0)), step=0.5, key=f"ac_{p_idx}")
        last_ret_t = tc4.time_input("🚨 Last Return:", value=default_last, key=f"lr_{p_idx}")

        base_dt = datetime.combine(datetime.today(), dep_t)
        arrival_dt = base_dt + timedelta(minutes=trans_m)
        finish_act_dt = arrival_dt + timedelta(hours=act_h)
        last_ret_dt = datetime.combine(datetime.today(), last_ret_t)
        buffer_mins = int((last_ret_dt - finish_act_dt).total_seconds() / 60)

        st.markdown(
            f"**🚆 Arrive:** `{arrival_dt.strftime('%H:%M')}` ➡️ "
            f"**🏁 Finish Activity:** `{finish_act_dt.strftime('%H:%M')}` ➡️ "
            f"**🚨 Last Return:** `{last_ret_dt.strftime('%H:%M')}`"
        )
        
        if buffer_mins >= 60:
            st.success(f"✅ **Safe Schedule!** You have **{buffer_mins // 60}h {buffer_mins % 60}m** spare buffer time before the last return ({last_ret_dt.strftime('%H:%M')}).")
        elif 0 <= buffer_mins < 60:
            st.warning(f"⚠️ **Tight Schedule!** Only **{buffer_mins} mins** spare before last return!")
        else:
            st.error(f"❌ **DANGER!** You finish at {finish_act_dt.strftime('%H:%M')}, missing the last return by **{abs(buffer_mins)} mins**!")

        # --- SURVIVAL & TICKETING CARDS ---
        st.markdown("#### 🛡️ 2. Local Transit Rules & Smart Ticketing")
        st.error(f"🚌 **Curfew Note:** {place['last_transit_note']}")
        st.warning(f"💳 **Local Payment Rule:** {place['payment_rule']}")
        st.info(f"🎟️ **Entry & Tickets:** {place['ticket_info']} | 💡 **Hack:** {place.get('saving_hack', 'N/A')} (Saved £{place.get('saved_gbp', 0)})")

        # --- INTERACTIVE CHECKPOINTS ---
        st.markdown("#### ☑️ 3. Step-by-Step Route Checkpoints")
        for c_i, cp in enumerate(place.get("checkpoints", [])):
            checked = st.checkbox(cp["task"], value=cp["done"], key=f"cp_{p_idx}_{c_i}")
            if checked != cp["done"]:
                place["checkpoints"][c_i]["done"] = checked
                save_data(data)

        c_add1, c_add2 = st.columns([3, 1])
        new_cp = c_add1.text_input("New step:", key=f"new_cp_{p_idx}", label_visibility="collapsed", placeholder="Add a checkpoint (e.g., Grab coffee in Lewes)...")
        if c_add2.button("➕ Add Step", key=f"btn_cp_{p_idx}") and new_cp:
            place.setdefault("checkpoints", []).append({"task": new_cp, "done": False})
            save_data(data)
            st.rerun()

        # --- PHOTO & MEMORY JOURNAL ---
        with st.expander("📸 Photo, Memories & Edit Trip Details"):
            if place.get("image_url"):
                st.image(place["image_url"], caption=f"{place['name']} — {place.get('mood', '')}", use_container_width=True)
            st.write(f"**💭 Memory / Notes:** {place.get('notes', '')}")
            st.divider()
            
            e1, e2, e3 = st.columns(3)
            new_paid = e1.number_input("Paid (£):", value=float(place.get("paid_gbp", 0.0)), step=0.5)
            new_saved = e2.number_input("Saved (£):", value=float(place.get("saved_gbp", 0.0)), step=0.5)
            new_rating = e3.slider("Rating (Stars):", 1, 5, int(place.get("rating", 5)))
            
            new_img = st.text_input("Photo URL (or paste image link):", value=place.get("image_url", ""))
            new_hack = st.text_input("Saving Hack Used:", value=place.get("saving_hack", ""))
            new_last_note = st.text_input("Curfew / Last Bus Warning:", value=place.get("last_transit_note", ""))
            new_pay_rule = st.text_input("Payment Rule:", value=place.get("payment_rule", ""))
            new_notes = st.text_area("Personal Journal & Memories:", value=place.get("notes", ""))
            
            if st.button("💾 Save All Changes", key=f"save_{p_idx}"):
                place.update({
                    "dep_time": dep_t.strftime("%H:%M"),
                    "transit_mins": trans_m,
                    "activity_hours": act_h,
                    "last_return": last_ret_t.strftime("%H:%M"),
                    "paid_gbp": new_paid,
                    "saved_gbp": new_saved,
                    "rating": new_rating,
                    "image_url": new_img,
                    "saving_hack": new_hack,
                    "last_transit_note": new_last_note,
                    "payment_rule": new_pay_rule,
                    "notes": new_notes
                })
                save_data(data)
                st.success("Trip updated!")
                st.rerun()

        q_clean = place["name"].split("(")[0].strip().replace(" ", "+")
        l1, l2, l3 = st.columns(3)
        l1.link_button("🚆 Google Maps Transit", f"https://www.google.com/maps/dir/Southampton+Central/{q_clean}/")
        l2.link_button("🥾 AllTrails Map", f"https://www.alltrails.com/search?q={q_clean}")
        l3.link_button("🎟️ Official Tickets", f"https://www.google.com/search?q={q_clean}+official+tickets+uk")

# === TAB 2: Door-to-Door UK Airport Comparison ===
with tab2:
    st.subheader("✈️ Door-to-Door Airport Cost Calculator (From Southampton)")
    dest = st.text_input("🌍 Target European Destination:", "Milan")
    airports = [
        {"name": "Bournemouth (BOH)", "code": "BOH", "transit": 8.0, "time": "45 mins (Train + Bus)", "flight": 22.0},
        {"name": "Southampton (SOU)", "code": "SOU", "transit": 5.5, "time": "10 mins (Direct Train)", "flight": 65.0},
        {"name": "Bristol (BRS) ⭐ Hidden Gem", "code": "BRS", "transit": 24.0, "time": "1h 45m (Direct Train + A1 Flyer)", "flight": 19.0},
        {"name": "London Gatwick (LGW)", "code": "LGW", "transit": 26.0, "time": "2h 00m (Train / Coach)", "flight": 28.0},
        {"name": "London Heathrow (LHR)", "code": "LHR", "transit": 28.0, "time": "1h 45m (National Express)", "flight": 55.0},
        {"name": "London Stansted / Luton (STN/LTN)", "code": "STN", "transit": 42.0, "time": "3h 15m (Train + Tube)", "flight": 14.0},
        {"name": "Birmingham (BHX) ⭐ Direct Train", "code": "BHX", "transit": 34.0, "time": "2h 30m (Direct CrossCountry!)", "flight": 20.0},
    ]
    results = []
    cols = st.columns(4)
    for idx, ap in enumerate(airports):
        with cols[idx % 4]:
            f_price = st.number_input(f"{ap['name']} Flight (£):", value=ap["flight"], step=1.0, key=ap["code"])
            results.append({**ap, "flight": f_price, "total": f_price + ap["transit"]})
    results.sort(key=lambda x: x["total"])
    best = results[0]
    st.success(f"🏆 **Smartest Choice: {best['name']}** | **Real Door-to-Door Total: £{best['total']:.2f}** (Flight £{best['flight']:.2f} + Return Transit £{best['transit']:.2f})")
    st.dataframe(results, use_container_width=True)

# === TAB 3: Live Expense Tracker ===
with tab3:
    st.subheader("💸 Live Trip Expense Logger (Multi-Currency)")
    with st.form("exp_form"):
        c1, c2, c3, c4 = st.columns(4)
        t_name = c1.text_input("Trip Name:", "Shaftesbury")
        i_name = c2.text_input("Item (e.g., Coffee, Bus):")
        amt = c3.number_input("Amount:", min_value=0.0, step=0.5)
        curr = c4.selectbox("Currency:", ["GBP (£)", "EUR (€) x0.85", "PLN (zł) x0.20", "HUF (Ft) x0.0021"])
        cat = st.selectbox("Category:", ["Transit 🚆🚌", "Food & Coffee ☕", "Accommodation 🏨", "Tickets 🎟️"])
        if st.form_submit_button("➕ Log Expense"):
            rates = {"GBP (£)": 1.0, "EUR (€) x0.85": 0.85, "PLN (zł) x0.20": 0.20, "HUF (Ft) x0.0021": 0.0021}
            gbp_val = round(amt * rates[curr], 2)
            data["expenses"].append({"date": datetime.now().strftime("%Y-%m-%d"), "trip": t_name, "item": i_name, "amount_gbp": gbp_val, "category": cat})
            save_data(data)
            st.success(f"Added {i_name} (£{gbp_val})!")
            st.rerun()
    st.dataframe(data["expenses"], use_container_width=True)

# === TAB 4: True Rolling 180-Day Schengen Calculator ===
with tab4:
    st.subheader("🛂 True Rolling 180-Day Schengen Calculator")
    st.write(f"The Schengen rule counts backwards **180 days from today ({win_start} to {date.today()})**. You have used **{used_schengen} / 90 days** ({schengen_left} days remaining).")
    
    with st.form("schengen_form"):
        sc1, sc2, sc3 = st.columns(3)
        s_country = sc1.text_input("Country / Trip Name:", placeholder="e.g., Spain (Barcelona)")
        s_start = sc2.date_input("Entry Date:", value=date.today())
        s_end = sc3.date_input("Exit Date:", value=date.today() + timedelta(days=4))
        if st.form_submit_button("➕ Add Schengen Trip"):
            if s_end >= s_start and s_country:
                data.setdefault("schengen_trips", []).append({
                    "country": s_country,
                    "start": s_start.strftime("%Y-%m-%d"),
                    "end": s_end.strftime("%Y-%m-%d")
                })
                save_data(data)
                st.success(f"Added {s_country} to Schengen log!")
                st.rerun()
    st.dataframe(data.get("schengen_trips", []), use_container_width=True)

# === TAB 5: Smart Auto-Geocode Add & AI Import ===
with tab5:
    col_man, col_ai = st.columns(2)
    with col_man:
        st.subheader("🔍 Smart Add (Auto-Coordinates & Distance)")
        st.caption("Just type the place name! The app will automatically find its coordinates and calculate the distance from Southampton.")
        search_q = st.text_input("1. Search Place Name:", placeholder="e.g., Bath, UK or Seven Sisters, UK")
        if "geo_res" not in st.session_state:
            st.session_state.geo_res = {"lat": 50.8194, "lon": -1.5786, "dist": 22, "name": ""}
            
        if st.button("🔍 Auto-Find Coordinates & Distance") and search_q:
            res = geocode_place(search_q)
            if res.get("ok"):
                st.session_state.geo_res = {"lat": res["lat"], "lon": res["lon"], "dist": res["dist"], "name": search_q}
                st.success(f"Found: {res['display_name']} ({res['dist']} km from Southampton!)")
            else:
                st.error("Could not find place automatically. Try adding ', UK' or ', Europe'.")

        with st.form("smart_manual_add"):
            m_name = st.text_input("Destination Title:", value=st.session_state.geo_res.get("name", ""))
            m_cat = st.selectbox("Category:", ["Historic Village", "Linear Hike / Nature", "Coastal Walk", "European City Break", "Food & Cafe Spot 🍔"])
            mc1, mc2, mc3 = st.columns(3)
            m_lat = mc1.number_input("Latitude:", value=float(st.session_state.geo_res["lat"]), format="%.4f")
            m_lon = mc2.number_input("Longitude:", value=float(st.session_state.geo_res["lon"]), format="%.4f")
            m_km = mc3.number_input("Distance from SOU (km):", value=int(st.session_state.geo_res["dist"]))
            m_last = st.text_input("Last Return Time (HH:MM):", "20:30")
            m_pay = st.text_input("Payment Rule:", "🟢 Contactless / Apple Pay OK")
            
            if st.form_submit_button("📌 Save Pin to My Map"):
                if m_name:
                    data["places"].append({
                        "id": len(data["places"]) + 1,
                        "name": m_name,
                        "country": "UK",
                        "category": m_cat,
                        "status": "wishlist",
                        "lat": m_lat,
                        "lon": m_lon,
                        "distance_km": m_km,
                        "rating": 5,
                        "paid_gbp": 0.0,
                        "saved_gbp": 0.0,
                        "saving_hack": "",
                        "dep_time": "09:00",
                        "transit_mins": 60,
                        "activity_hours": 4.0,
                        "last_return": m_last,
                        "last_transit_note": f"Last return train/bus at {m_last}",
                        "payment_rule": m_pay,
                        "ticket_info": "🆓 Check official site",
                        "mood": "🌲 Planned adventure",
                        "notes": "",
                        "image_url": "",
                        "checkpoints": []
                    })
                    save_data(data)
                    st.success(f"Added {m_name} to your map!")
                    st.rerun()

    with col_ai:
        st.subheader("🤖 Paste AI JSON Snippet")
        json_str = st.text_area("JSON Input:", height=280)
        if st.button("🚀 Import JSON to Map"):
            try:
                new_p = json.loads(json_str)
                new_p["id"] = len(data["places"]) + 1
                data["places"].append(new_p)
                save_data(data)
                st.success(f"Imported {new_p['name']} successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
