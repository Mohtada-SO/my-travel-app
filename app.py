import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import os
from datetime import datetime

# إعدادات الصفحة لتناسب الجوال واللابتوب
st.set_page_config(page_title="أطلس رحلاتي | ساوثهامبتون وأوروبا", page_icon="🌍", layout="wide")

DATA_FILE = "my_travel_data.json"

# بيانات تجريبية أولية (تشمل طلعتك لشافتسبري + هايك ساوث داونز + دورست)
DEFAULT_DATA = {
    "places": [
        {
            "id": 1,
            "name": "Shaftesbury (Gold Hill)",
            "country": "UK",
            "category": "قرية تاريخية",
            "status": "visited", # visited, wishlist, food
            "lat": 51.0045,
            "lon": -2.1983,
            "distance_km": 68,
            "paid_gbp": 14.50,
            "saved_gbp": 12.00,
            "saving_type": "توفير مؤكد (Railcard + £2 Bus Cap)",
            "last_transit": "آخر باص (X2/B3) إلى محطة Gillingham الساعة 17:38",
            "payment_rule": "🟢 يقبل Contactless / Apple Pay في الباص",
            "ticket_info": "🆓 دخول القرية ومطل Gold Hill مجاني 24 ساعة",
            "mood": "😌 راحة بال وإطلالة ريفية كلاسيكية",
            "notes": "النزول كان في محطة Gillingham ثم باص. توقيت الباصات كل ساعة تقريباً فلازم انتباه لوقت العودة.",
            "date": "2026-10-16"
        },
        {
            "id": 2,
            "name": "South Downs Hike (Hassocks to Lewes)",
            "country": "UK",
            "category": "مسار هايكنج خطي (17 كم)",
            "status": "wishlist",
            "lat": 50.9086,
            "lon": -0.1072,
            "distance_km": 115,
            "paid_gbp": 20.70,
            "saved_gbp": 18.00,
            "saving_type": "توفير ذكي (Return to Lewes + Single بدلاً من تذكرتين منفصلتين)",
            "last_transit": "🚨 الغروب 18:05 | آخر قطار مباشر من Brighton لساوثهامبتون 21:02",
            "payment_rule": "🟢 القطار ببطاقة Railcard | باص الطوارئ (Breeze 79) عند القمة بـ £2 Apple Pay",
            "ticket_info": "🆓 مسار طبيعي مجاني - ⚠️ لا يوجد ماء أو بقالات طول الـ 17 كم!",
            "mood": "🤩 حماس وتحدي طبيعي",
            "notes": "الانطلاق من محطة Hassocks رصيف 2 -> طواحين Jack and Jill -> قمة Ditchling Beacon -> النزول لبلدة Lewes.",
            "date": "2026-10-24"
        },
        {
            "id": 3,
            "name": "Durdle Door & Lulworth Cove",
            "country": "UK",
            "category": "ساحل وطبيعة",
            "status": "wishlist",
            "lat": 50.6212,
            "lon": -2.2768,
            "distance_km": 75,
            "paid_gbp": 0.0,
            "saved_gbp": 0.0,
            "saving_type": "",
            "last_transit": "قطار إلى محطة Wool ثم باص Morebus 30 (ينتهي مبكراً في الشتاء!)",
            "payment_rule": "🟢 يقبل Contactless (لا تنسَ Tap Off عند النزول!)",
            "ticket_info": "🆓 الشاطئ مجاني تماماً",
            "mood": "🌊 استكشاف قادم",
            "notes": "أفضل وقت للزيارة يوم مشمس والغروب واضح.",
            "date": ""
        }
    ],
    "expenses": [
        {"date": "2026-10-16", "trip": "Shaftesbury", "item": "تذكرة قطار إلى Gillingham", "amount_gbp": 10.50, "category": "مواصلات 🚆"},
        {"date": "2026-10-16", "trip": "Shaftesbury", "item": "باص ذهاب وعودة", "amount_gbp": 4.00, "category": "مواصلات 🚌"},
        {"date": "2026-10-16", "trip": "Shaftesbury", "item": "قهوة وسناك", "amount_gbp": 5.20, "category": "أكل وقهوة ☕"}
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

# ----------------- الهيدر ولوحة الإحصائيات العلوية -----------------
st.title("🌍 أطلس رحلاتي الذكي | ساوثهامبتون وأوروبا")

visited_places = [p for p in data["places"] if p["status"] == "visited"]
total_km = sum(p.get("distance_km", 0) * 2 for p in visited_places)
total_paid = sum(e.get("amount_gbp", 0) for e in data["expenses"])
total_saved = sum(p.get("saved_gbp", 0) for p in data["places"])
schengen_left = 90 - data.get("schengen_days_used", 0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("📍 أماكن زرتها / بالقائمة", f"{len(visited_places)} / {len(data['places'])}", "انطلاقاً من ساوثهامبتون")
col2.metric("💰 إجمالي المصروف الفعلي", f"£{total_paid:.2f}", f"وفّرت بذكائك: £{total_saved:.2f} 🔥")
col3.metric("📏 المسافات المقطوعة", f"{total_km} كم", "قطارات، باصات، ومشي")
col4.metric("🛂 رصيد الشنقن (90/180)", f"باقي {schengen_left} يوم", f"استهلكت {data.get('schengen_days_used', 0)} يوم")

st.divider()

# ----------------- التبويبات الـ 4 الأساسية -----------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ الخريطة والرادار", 
    "✈️ محرك التوفير والمطارات", 
    "💸 وضع السفرة الحية (تسجيل سريع)", 
    "📋 إضافة مكان / لصق من الشات"
])

# === التبويب الأول: الخريطة والبطاقات ===
with tab1:
    c_map, c_details = st.columns([3, 2])
    
    with c_map:
        st.subheader("خريطة دبابيسي التفاعلية")
        # مركز الخريطة: ساوثهامبتون
        m = folium.Map(location=[50.9097, -1.4044], zoom_start=8, tiles="CartoDB positron")
        
        # دبوس ساوثهامبتون (المركز الأساسي)
        folium.Marker(
            [50.9097, -1.4044],
            popup="🏠 سكن ساوثهامبتون (نقطة الانطلاق)",
            tooltip="🏠 ساوثهامبتون (المركز)",
            icon=folium.Icon(color="black", icon="home")
        ).add_to(m)

        # إضافة دبابيس الأماكن
        for p in data["places"]:
            color = "green" if p["status"] == "visited" else ("orange" if p["status"] == "food" else "blue")
            status_label = "✅ زرته" if p["status"] == "visited" else ("🍔 مطعم/كافيه" if p["status"] == "food" else "🟡 ودي أروحه")
            popup_html = f"""
            <div style="direction:rtl; text-align:right; font-family:sans-serif; width:220px;">
                <b>{p['name']}</b> ({status_label})<br>
                <small>{p['category']}</small><hr style="margin:4px 0;">
                🚌 <b>آخر مواصلات:</b> {p['last_transit']}<br>
                💳 <b>الدفع:</b> {p['payment_rule']}<br>
                🎟️ <b>التذاكر:</b> {p['ticket_info']}
            </div>
            """
            folium.Marker(
                [p["lat"], p["lon"]],
                popup=folium.Popup(popup_html, max_width=260),
                tooltip=f"{p['name']} ({status_label})",
                icon=folium.Icon(color=color, icon="info-sign")
            ).add_to(m)
            
        st_folium(m, width=700, height=480)

    with c_details:
        st.subheader("📖 بطاقة تفاصيل المكان وطوق النجاة")
        selected_name = st.selectbox("اختر مكاناً لعرض خطته الكاملة وخواطرك:", [p["name"] for p in data["places"]])
        place = next(p for p in data["places"] if p["name"] == selected_name)
        
        badge = "🟢 تمت الزيارة" if place["status"] == "visited" else "🟡 مخطط لها (Wishlist)"
        st.markdown(f"### {place['name']} | `{badge}`")
        st.caption(f"التصنيف: {place['category']} | البعد عن ساوثهامبتون: {place['distance_km']} كم")
        
        st.error(f"🚨 **طوق النجاة (آخر موعد للعودة):**\n\n{place['last_transit']}")
        st.warning(f"💳 **نظام الدفع المحلي والباصات:**\n\n{place['payment_rule']}")
        st.info(f"🎟️ **معلومات الدخول والتذاكر:**\n\n{place['ticket_info']}")
        
        if place.get("saved_gbp", 0) > 0:
            st.success(f"💰 **حركة التوفير:** وفّرت **£{place['saved_gbp']}** ({place['saving_type']})")
            
        st.markdown(f"**💭 الخواطر والملاحظات ({place['mood']}):**")
        st.write(place["notes"])
        
        # أزرار الروابط الحقيقية السريعة
        q_name = place["name"].split("(")[0].strip().replace(" ", "+")
        st.markdown("#### 🔗 روابط التخطيط والحجز المباشرة:")
        b1, b2, b3 = st.columns(3)
        b1.link_button("🚆 مسار القطار/الباص", f"https://www.google.com/maps/dir/Southampton+Central/{q_name}/")
        b2.link_button("🥾 مسار AllTrails", f"https://www.alltrails.com/search?q={q_name}")
        b3.link_button("🎟️ فحص التذاكر الرسمية", f"https://www.google.com/search?q={q_name}+official+tickets+student+discount")

# === التبويب الثاني: محرك مقارنة المطارات من ساوثهامبتون ===
with tab2:
    st.subheader("✈️ حاسبة التكلفة الحقيقية للمطارات (من باب سكنك في ساوثهامبتون)")
    st.write("أدخل سعر تذكرة الطيران التي وجدتها في أي مطار، وسيحسب لك النظام **التكلفة الإجمالية مع القطار/الباص من ساوثهامبتون** ليكشف لك أيها أرخص فعلاً!")
    
    dest = st.text_input("🌍 الوجهة الأوروبية (مثال: Milan, Krakow, Geneva):", "Milan")
    
    airports = [
        {"name": "مطار بورنموث (BOH)", "code": "BOH", "transit_cost": 8.0, "time": "45 دقيقة (قطار + باص)", "default_flight": 22.0},
        {"name": "مطار ساوثهامبتون (SOU)", "code": "SOU", "transit_cost": 5.5, "time": "10 دقائق فقط!", "default_flight": 65.0},
        {"name": "مطار بريستول (BRS) ⭐ صيدة!", "code": "BRS", "transit_cost": 24.0, "time": "ساعة و45 دقيقة (قطار مباشر + Flyer)", "default_flight": 19.0},
        {"name": "لندن جاتويك (LGW)", "code": "LGW", "transit_cost": 26.0, "time": "ساعتين (قطار أو National Express)", "default_flight": 28.0},
        {"name": "لندن هيثرو (LHR)", "code": "LHR", "transit_cost": 28.0, "time": "ساعة و45 دقيقة (باص مباشر)", "default_flight": 55.0},
        {"name": "لندن لوتون / ستانستيد (LTN/STN)", "code": "STN", "transit_cost": 42.0, "time": "3 ساعات و15 دقيقة (قطار + مترو)", "default_flight": 14.0},
    ]
    
    results = []
    cols = st.columns(3)
    for idx, ap in enumerate(airports):
        with cols[idx % 3]:
            flight_price = st.number_input(f"سعر الطيران من {ap['name']} (£):", value=ap["default_flight"], step=1.0, key=ap["code"])
            total_real_cost = flight_price + ap["transit_cost"]
            results.append({"airport": ap["name"], "code": ap["code"], "total": total_real_cost, "flight": flight_price, "transit": ap["transit_cost"], "time": ap["time"]})
            
    results.sort(key=lambda x: x["total"])
    best = results[0]
    
    st.success(f"🏆 **الخيار الأذكى والأوفر فعلياً هو: {best['airport']}** بتكلفة إجمالية **£{best['total']:.2f}** (شاملة الطيران £{best['flight']} + مواصلات ساوثهامبتون ذهاب وعودة £{best['transit']}) | وقت الطريق: {best['time']}")
    
    st.markdown("#### 🔗 افتح الحجز المباشر للوجهة:")
    l1, l2, l3, l4 = st.columns(4)
    l1.link_button("✈️ Skyscanner (كل بريطانيا)", f"https://www.skyscanner.net/transport/flights-from/uk/?oym=2610&selectedoday=01")
    l2.link_button("🏨 Booking.com (الأرخص)", f"https://www.booking.com/searchresults.html?ss={dest}&order=price")
    l3.link_button("🏡 Airbnb", f"https://www.airbnb.co.uk/s/{dest}/homes")
    l4.link_button("🚌 Rome2Rio (المسار الكامل)", f"https://www.rome2rio.com/map/Southampton/{dest}")

# === التبويب الثالث: تسجيل المصاريف السريع ===
with tab3:
    st.subheader("💸 مسجل المصاريف اليومي اللحظي (مع محول العملات)")
    with st.form("expense_form"):
        c1, c2, c3, c4 = st.columns(4)
        trip_name = c1.text_input("اسم الرحلة / المدينة:", "Shaftesbury")
        item_name = c2.text_input("شنو دفعت؟ (قهوة، باص، غداء):")
        amount = c3.number_input("المبلغ:", min_value=0.0, step=0.5)
        currency = c4.selectbox("العملة:", ["GBP (£)", "EUR (€) -> x0.85", "PLN (زلوتي بولندي) -> x0.20", "HUF (فورنت مجري) -> x0.0021"])
        cat = st.selectbox("التصنيف:", ["أكل وقهوة ☕", "مواصلات 🚆🚌", "سكن 🏨", "تذاكر وأنشطة 🎟️"])
        
        if st.form_submit_button("➕ سجل المصروف فوراً"):
            rates = {"GBP (£)": 1.0, "EUR (€) -> x0.85": 0.85, "PLN (زلوتي بولندي) -> x0.20": 0.20, "HUF (فورنت مجري) -> x0.0021": 0.0021}
            gbp_val = round(amount * rates[currency], 2)
            data["expenses"].append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "trip": trip_name,
                "item": item_name,
                "amount_gbp": gbp_val,
                "category": cat
            })
            save_data(data)
            st.success(f"تم تسجيل {item_name} بقيمة £{gbp_val} بنجاح!")
            st.rerun()

    st.markdown("#### 📊 سجل مصاريفك:")
    st.dataframe(data["expenses"], use_container_width=True)

# === التبويب الرابع: اللصق السريع من الشات ===
with tab4:
    st.subheader("📋 الإضافة السريعة من الشات (Quick JSON Import)")
    st.write("لما ترسل لي صورة أو رابط تيك توك في الشات، أعطيك كود جاهز، الصقه هنا بضغطة زر وينزل في خريطتك بكل تفاصيله!")
    
    sample_json = {
        "name": "Cotswolds (Castle Combe)",
        "country": "UK",
        "category": "قرية تاريخية",
        "status": "wishlist",
        "lat": 51.4922,
        "lon": -2.2285,
        "distance_km": 95,
        "paid_gbp": 0.0,
        "saved_gbp": 9.5,
        "saving_type": "Split Ticket via Salisbury",
        "last_transit": "آخر باص ( رقم 35 ) من القرية إلى محطة Chippenham الساعة 18:10",
        "payment_rule": "🟢 يقبل Contactless في باص Faresaver",
        "ticket_info": "🆓 دخول القرية مجاني تماماً",
        "mood": "🍂 خريف وهدوء",
        "notes": "أجمل قرية في إنجلترا، الوصول بالقطار إلى محطة Chippenham ثم باص 20 دقيقة.",
        "date": "2026-11-01"
    }
    
    json_input = st.text_area("الصق الكود السريع هنا:", value=json.dumps(sample_json, ensure_ascii=False, indent=2), height=220)
    if st.button("🚀 افحص وأضف المكان للخريطة"):
        try:
            new_place = json.loads(json_input)
            new_place["id"] = len(data["places"]) + 1
            data["places"].append(new_place)
            save_data(data)
            st.success(f"✅ تمت إضافة {new_place['name']} إلى خريطتك بنجاح!")
            st.rerun()
        except Exception as e:
            st.error(f"تأكد من صيغة الكود: {e}")
