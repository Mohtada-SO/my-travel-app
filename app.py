import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os
from datetime import datetime, time, timedelta

st.set_page_config(page_title="Southampton & Europe Travel Atlas", page_icon="🌍", layout="wide")

DATA_FILE = "travel_atlas_en.json"

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
            "distance_km": 115,
            "paid_gbp": 20.70,
            "saved_gbp": 18.00,
            "saving_hack": "Off-Peak Day Return to Lewes + short Single (Brighton-Hassocks) instead of 2 expensive Singles!",
            "dep_time": "08:30",
            "transit_mins": 132,
            "activity_hours": 4.5,
            "last_return": "21:02",
            "last_transit_note": "🚨 Sunset at 18:05! Last direct Brighton->Southampton train at 21:02",
            "payment_rule": "🟢 Use Railcard on App | Emergency Breeze Bus 79 at Ditchling Beacon (£2 Apple Pay)",
            "ticket_info": "🆓 Free trail - ⚠️ NO water/shops along the 17km ridge!",
            "mood": "🤩 Excited for the ridge views",
            "notes": "Exit Hassocks Platform 2 -> Jack & Jill Windmills -> Ditchling Beacon (248m peak) -> Descend into Lewes town.",
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
            "distance_km": 75,
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
    "schengen_days_used": 12
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

# ----------------- Top Metrics Dashboard -----------------
st.title("🌍 Smart Travel Planner & Memory Atlas")
st.caption("Base Hub: Southampton, UK ⚓ | Live Trip Builder, Curfew Calculator & Expense Tracker")

visited_places = [p for p in data["places"] if p["status"] == "visited"]
total_km = sum(p.get("distance_km", 0) * 2 for p in visited_places)
total_paid = sum(e.get("amount_gbp", 0) for e in data["expenses"])
total_saved = sum(p.get("saved_gbp", 0) for p in data["places"])
schengen_left = 90 - data.get("schengen_days_used", 0)

m1, m2, m3, m4 = st.columns(4)
m1.metric("📍 Visited / Total Pins", f"{len(visited_places)} / {len(data['places'])}", "From Southampton Hub")
m2.metric("💰 Total Spent", f"£{total_paid:.2f}", f"Smart Saved: £{total_saved:.2f} 🔥")
m3.metric("📏 Distance Covered", f"{total_km} km", "Round-trip from SOU")
m4.metric("🛂 Schengen Quota (90/180)", f"{schengen_left} Days Left", f"{data.get('schengen_days_used', 0)} days used")

st.divider()

# ----------------- Main Navigation Tabs -----------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ Map & Live Trip Planner", 
    "✈️ UK Airport Matrix", 
    "💸 Expense Tracker", 
    "➕ Add New Trip / Quick Import"
])

# === TAB 1: Map & Interactive Planner ===
with tab1:
    col_map, col_plan = st.columns([1.2, 1.3])
    
    with col_map:
        st.subheader("📍 Interactive Pin Map")
        # Clean OpenStreetMap tiles (No API key watermark!)
        m = folium.Map(location=[50.9097, -1.4044], zoom_start=8)
        
        folium.Marker(
            [50.9097, -1.4044],
            popup="🏠 Southampton Base Hub",
            tooltip="🏠 Southampton (Home Base)",
            icon=folium.Icon(color="black", icon="home")
        ).add_to(m)

        for p in data["places"]:
            color = "green" if p["status"] == "visited" else ("orange" if p["status"] == "food" else "blue")
            status_tag = "VISITED" if p["status"] == "visited" else "WISHLIST"
            popup_html = f"""
            <div style="font-family:sans-serif; width:210px;">
                <b>{p['name']}</b> <span style="color:gray;">({status_tag})</span><br>
                <small>{p['category']}</small><hr style="margin:5px 0;">
                🚨 <b>Last Return:</b> {p['last_return']}<br>
                💳 <b>Payment:</b> {p['payment_rule']}<br>
                💰 <b>Saved:</b> £{p.get('saved_gbp', 0)}
            </div>
            """
            folium.Marker(
                [p["lat"], p["lon"]],
                popup=folium.Popup(popup_html, max_width=240),
                tooltip=f"{p['name']} ({status_tag})",
                icon=folium.Icon(color=color, icon="info-sign")
            ).add_to(m)
            
        st_folium(m, width=600, height=500)

    with col_plan:
        st.subheader("🛠️ Interactive Trip Planner & Survival Guide")
        
        place_names = [p["name"] for p in data["places"]]
        selected_name = st.selectbox("Select Destination to Plan or Edit:", place_names)
        p_idx = next(i for i, p in enumerate(data["places"]) if p["name"] == selected_name)
        place = data["places"][p_idx]
        
        # Status Toggle Button
        status_col1, status_col2 = st.columns([2, 1])
        badge = "🟢 VISITED" if place["status"] == "visited" else "🟡 WISHLIST (PLANNED)"
        status_col1.markdown(f"### {place['name']} `{badge}`")
        if status_col2.button("🔄 Toggle Visited / Wishlist"):
            place["status"] = "visited" if place["status"] != "visited" else "wishlist"
            save_data(data)
            st.rerun()

        # --- LIVE REVERSE TIMELINE CALCULATOR ---
        st.markdown("#### ⏱️ 1. Live Day-Trip Timeline & Curfew Calculator")
        tc1, tc2, tc3, tc4 = st.columns(4)
        
        try:
            default_dep = datetime.strptime(place.get("dep_time", "08:30"), "%H:%M").time()
            default_last = datetime.strptime(place.get("last_return", "18:00"), "%H:%M").time()
        except:
            default_dep = time(8, 30)
            default_last = time(18, 0)

        dep_t = tc1.time_input("Leave Southampton:", value=default_dep, key=f"dep_{p_idx}")
        trans_m = tc2.number_input("Transit (mins):", value=int(place.get("transit_mins", 90)), step=5, key=f"tr_{p_idx}")
        act_h = tc3.number_input("Hike/Explore (hrs):", value=float(place.get("activity_hours", 4.0)), step=0.5, key=f"ac_{p_idx}")
        last_ret_t = tc4.time_input("🚨 Last Return Bus/Train:", value=default_last, key=f"lr_{p_idx}")

        # Calculate Exact Schedule
        base_dt = datetime.combine(datetime.today(), dep_t)
        arrival_dt = base_dt + timedelta(minutes=trans_m)
        finish_act_dt = arrival_dt + timedelta(hours=act_h)
        last_ret_dt = datetime.combine(datetime.today(), last_ret_t)
        buffer_mins = int((last_ret_dt - finish_act_dt).total_seconds() / 60)

        st.markdown(
            f"**🚆 Arrive at Destination:** `{arrival_dt.strftime('%H:%M')}` ➡️ "
            f"**🏁 Finish Hike/Activity:** `{finish_act_dt.strftime('%H:%M')}` ➡️ "
            f"**🚨 Last Return Transit:** `{last_ret_dt.strftime('%H:%M')}`"
        )
        
        if buffer_mins >= 60:
            st.success(f"✅ **Safe Schedule!** You have **{buffer_mins // 60} hr {buffer_mins % 60} mins** of spare buffer time (for coffee/food/delays) before the last return at {last_ret_dt.strftime('%H:%M')}.")
        elif 0 <= buffer_mins < 60:
            st.warning(f"⚠️ **Tight Schedule!** Only **{buffer_mins} mins** spare before the last return transit! Consider leaving Southampton earlier.")
        else:
            st.error(f"❌ **DANGER!** You will finish at {finish_act_dt.strftime('%H:%M')}, missing the last return ({last_ret_dt.strftime('%H:%M')}) by **{abs(buffer_mins)} mins**! Leave earlier!")

        # --- SURVIVAL & TICKETING CARDS ---
        st.markdown("#### 🛡️ 2. Local Transit Rules & Smart Ticketing")
        st.error(f"🚌 **Curfew Note:** {place['last_transit_note']}")
        st.warning(f"💳 **Local Payment Rule:** {place['payment_rule']}")
        st.info(f"🎟️ **Entry & Tickets:** {place['ticket_info']} | 💡 **Hack:** {place.get('saving_hack', 'N/A')} (Saved £{place.get('saved_gbp', 0)})")

        # --- INTERACTIVE CHECKPOINTS ---
        st.markdown("#### ☑️ 3. Step-by-Step Route Checkpoints")
        checkpoints = place.get("checkpoints", [])
        for c_i, cp in enumerate(checkpoints):
            checked = st.checkbox(cp["task"], value=cp["done"], key=f"cp_{p_idx}_{c_i}")
            if checked != cp["done"]:
                place["checkpoints"][c_i]["done"] = checked
                save_data(data)

        new_cp = st.text_input("Add a new step/checkpoint to this trip:", key=f"new_cp_{p_idx}", placeholder="e.g., Grab pastry at Lewes Bakery before train")
        if st.button("➕ Add Step", key=f"btn_cp_{p_idx}") and new_cp:
            place.setdefault("checkpoints", []).append({"task": new_cp, "done": False})
            save_data(data)
            st.rerun()

        # --- EDIT TRIP DETAILS EXPANDER ---
        with st.expander("✏️ Edit Trip Prices, Rules & Notes"):
            new_paid = st.number_input("Actual Paid (£):", value=float(place.get("paid_gbp", 0.0)), step=0.5)
            new_saved = st.number_input("Amount Saved (£):", value=float(place.get("saved_gbp", 0.0)), step=0.5)
            new_hack = st.text_input("Saving Hack Used:", value=place.get("saving_hack", ""))
            new_last_note = st.text_input("Curfew / Last Bus Warning:", value=place.get("last_transit_note", ""))
            new_pay_rule = st.text_input("Payment Rule (Cash/Card/App):", value=place.get("payment_rule", ""))
            new_notes = st.text_area("Personal Notes & Memories:", value=place.get("notes", ""))
            
            if st.button("💾 Save All Changes", key=f"save_{p_idx}"):
                place["dep_time"] = dep_t.strftime("%H:%M")
                place["transit_mins"] = trans_m
                place["activity_hours"] = act_h
                place["last_return"] = last_ret_t.strftime("%H:%M")
                place["paid_gbp"] = new_paid
                place["saved_gbp"] = new_saved
                place["saving_hack"] = new_hack
                place["last_transit_note"] = new_last_note
                place["payment_rule"] = new_pay_rule
                place["notes"] = new_notes
                save_data(data)
                st.success("Trip updated successfully!")
                st.rerun()

        # --- EXTERNAL RESEARCH LINKS ---
        q_clean = place["name"].split("(")[0].strip().replace(" ", "+")
        l1, l2, l3 = st.columns(3)
        l1.link_button("🚆 Google Maps Transit", f"https://www.google.com/maps/dir/Southampton+Central/{q_clean}/")
        l2.link_button("🥾 AllTrails Map", f"https://www.alltrails.com/search?q={q_clean}")
        l3.link_button("🎟️ Official Tickets", f"https://www.google.com/search?q={q_clean}+official+tickets+uk")

# === TAB 2: Door-to-Door UK Airport Comparison ===
with tab2:
    st.subheader("✈️ Door-to-Door Airport Cost Calculator (From Southampton)")
    st.write("Compare total cost (**Flight + Return Train/Coach from Southampton**) across UK airports so cheap flights don't trick you with expensive London transit!")
    
    dest = st.text_input("🌍 Target European Destination:", "Milan")
    
    airports = [
        {"name": "Bournemouth (BOH)", "code": "BOH", "transit": 8.0, "time": "45 mins (Train + Bus)", "flight": 22.0},
        {"name": "Southampton (SOU)", "code": "SOU", "transit": 5.5, "time": "10 mins (Direct Train)", "flight": 65.0},
        {"name": "Bristol (BRS) ⭐ Hidden Gem", "code": "BRS", "transit": 24.0, "time": "1h 45m (Direct Train + A1 Flyer)", "flight": 19.0},
        {"name": "London Gatwick (LGW)", "code": "LGW", "transit": 26.0, "time": "2h 00m (Train / Coach)", "flight": 28.0},
        {"name": "London Heathrow (LHR)", "code": "LHR", "transit": 28.0, "time": "1h 45m (National Express)", "flight": 55.0},
        {"name": "London Stansted / Luton (STN/LTN)", "code": "STN", "transit": 42.0, "time": "3h 15m (Train + Tube + Express)", "flight": 14.0},
        {"name": "Birmingham (BHX) ⭐ Direct Train", "code": "BHX", "transit": 34.0, "time": "2h 30m (Direct CrossCountry Train!)", "flight": 20.0},
    ]
    
    results = []
    cols = st.columns(4)
    for idx, ap in enumerate(airports):
        with cols[idx % 4]:
            f_price = st.number_input(f"{ap['name']} Flight (£):", value=ap["flight"], step=1.0, key=ap["code"])
            total_c = f_price + ap["transit"]
            results.append({**ap, "flight": f_price, "total": total_c})
            
    results.sort(key=lambda x: x["total"])
    best = results[0]
    
    st.success(
        f"🏆 **Smartest Choice: {best['name']}** | **Real Total: £{best['total']:.2f}** "
        f"(Flight: £{best['flight']:.2f} + Southampton Return Transit: £{best['transit']:.2f}) | Travel Time: {best['time']}"
    )
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
            data["expenses"].append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "trip": t_name,
                "item": i_name,
                "amount_gbp": gbp_val,
                "category": cat
            })
            save_data(data)
            st.success(f"Added {i_name} (£{gbp_val})!")
            st.rerun()
            
    st.dataframe(data["expenses"], use_container_width=True)

# === TAB 4: Add New Trip Manually or via AI JSON ===
with tab4:
    col_man, col_ai = st.columns(2)
    
    with col_man:
        st.subheader("➕ Add Destination Manually")
        with st.form("manual_add"):
            m_name = st.text_input("Destination Name:", placeholder="e.g., New Forest (Brockenhurst)")
            m_cat = st.text_input("Category:", "Day Trip / Nature")
            mc1, mc2, mc3 = st.columns(3)
            m_lat = mc1.number_input("Latitude:", value=50.8194, format="%.4f")
            m_lon = mc2.number_input("Longitude:", value=-1.5786, format="%.4f")
            m_km = mc3.number_input("Distance from SOU (km):", value=22)
            m_last = st.text_input("Last Return Time (HH:MM):", "21:30")
            m_pay = st.text_input("Payment Rule:", "🟢 Contactless OK")
            
            if st.form_submit_button("📌 Save to My Map"):
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
                        "paid_gbp": 0.0,
                        "saved_gbp": 0.0,
                        "saving_hack": "",
                        "dep_time": "09:00",
                        "transit_mins": 30,
                        "activity_hours": 4.0,
                        "last_return": m_last,
                        "last_transit_note": f"Last return train/bus at {m_last}",
                        "payment_rule": m_pay,
                        "ticket_info": "🆓 Free entry",
                        "mood": "🌲 Exploring",
                        "notes": "",
                        "checkpoints": []
                    })
                    save_data(data)
                    st.success(f"Added {m_name} to your map!")
                    st.rerun()

    with col_ai:
        st.subheader("🤖 Paste AI JSON Snippet")
        st.caption("Paste the JSON code from our chat to auto-fill all transit rules, checkpoints & coordinates.")
        json_str = st.text_area("JSON Input:", height=240)
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
