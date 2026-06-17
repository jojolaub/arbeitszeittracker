import streamlit as st
import pandas as pd
import datetime
import os

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Arbeitszeit", page_icon="⏱️", layout="centered")

st.markdown("""
    <style>
    .metric-box { background-color: #f0f2f6; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
    .today-box { padding: 15px; border: 2px solid #4CAF50; border-radius: 12px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- SETUP & DATEN LADEN ---
username = st.sidebar.text_input("👤 Nutzername:", value="jojo").strip().lower()
filename = f"{username}_worklog.csv"
SOLL_STUNDEN_PRO_TAG = 8.0
URLAUB_KONTINGENT = 30

def load_data(file):
    if os.path.exists(file):
        df = pd.read_csv(file)
        df['Datum'] = pd.to_datetime(df['Datum']).dt.date
        if 'Urlaub' not in df.columns: df['Urlaub'] = False
        return df
    return pd.DataFrame(columns=["Datum", "Beginn", "Ende", "Pause_Min", "Krank", "Urlaub", "Wochenende", "Ist_Stunden", "Soll_Stunden", "Ueberstunden"])

def save_data(df, file):
    df.to_csv(file, index=False)

# Mathematische Umrechnung: Dezimal zu Sexagesimal (z.B. 6.25 -> 6h 15min)
def format_time(decimal_hours):
    if pd.isna(decimal_hours): return "0h 00min"
    sign = "+" if decimal_hours >= 0 else "-"
    val = abs(decimal_hours)
    h = int(val)
    m = int(round((val - h) * 60))
    if m == 60:
        h += 1
        m = 0
    return f"{sign}{h}h {m:02d}min"

df_entries = load_data(filename)
today = datetime.date.today()

st.title("⏱️ Arbeitszeit")

# --- 1. SCHNELLZUGRIFF: HEUTIGER TAG (Direkt oben) ---
st.markdown("<div class='today-box'>", unsafe_allow_html=True)
st.subheader("📍 Heutiger Arbeitstag")
st.write(f"**{today.strftime('%d.%m.%Y')}**")

# Prüfen, ob für heute schon etwas gespeichert wurde (für Updates im Laufe des Tages)
today_data = df_entries[df_entries["Datum"] == today]

if not today_data.empty:
    row = today_data.iloc[0]
    t_sick, t_vac, t_week = bool(row["Krank"]), bool(row["Urlaub"]), bool(row["Wochenende"])
    t_pause = int(row["Pause_Min"])
    try: t_start = datetime.datetime.strptime(str(row["Beginn"]), "%H:%M").time()
    except: t_start = datetime.time(8, 0)
    try: t_end = datetime.datetime.strptime(str(row["Ende"]), "%H:%M").time()
    except: t_end = datetime.datetime.now().time()
else:
    # Standardwerte für einen neuen Tag
    t_sick, t_vac, t_week = False, False, False
    t_pause = 30
    t_start = datetime.time(8, 0)
    t_end = datetime.datetime.now().time() # Setzt Ende dynamisch auf jetzige Uhrzeit

c1, c2, c3 = st.columns(3)
is_sick_today = c1.checkbox("🤒 Krank", value=t_sick, key="tod_s")
is_vac_today = c2.checkbox("🏖️ Urlaub", value=t_vac, key="tod_v")
is_week_today = c3.checkbox("📅 Wochenende", value=t_week, key="tod_w")

if not (is_sick_today or is_vac_today):
    col1, col2, col3 = st.columns(3)
    start_today = col1.time_input("Beginn:", value=t_start, key="tod_start")
    end_today = col2.time_input("Ende:", value=t_end, key="tod_end")
    pause_today = col3.number_input("Pause (Min):", min_value=0, max_value=120, value=t_pause, step=5, key="tod_pause")
else:
    start_today, end_today, pause_today = datetime.time(0,0), datetime.time(0,0), 0

if st.button("💾 Heutigen Tag speichern / updaten", use_container_width=True):
    if is_sick_today or is_vac_today:
        ist_h, soll_h = 0.0, 0.0 # Neutrales Element für die Arbeitszeit
    else:
        diff_sec = (datetime.datetime.combine(today, end_today) - datetime.datetime.combine(today, start_today)).total_seconds()
        if diff_sec < 0: diff_sec += 86400 # Falls über Mitternacht gearbeitet wird
        ist_h = (diff_sec / 3600) - (pause_today / 60)
        soll_h = 0.0 if is_week_today else SOLL_STUNDEN_PRO_TAG
        
    ueber_h = ist_h - soll_h
    new_today_row = {
        "Datum": today,
        "Beginn": "Frei" if (is_sick_today or is_vac_today) else start_today.strftime("%H:%M"),
        "Ende": "Frei" if (is_sick_today or is_vac_today) else end_today.strftime("%H:%M"),
        "Pause_Min": pause_today,
        "Krank": is_sick_today,
        "Urlaub": is_vac_today,
        "Wochenende": is_week_today,
        "Ist_Stunden": round(ist_h, 2),
        "Soll_Stunden": round(soll_h, 2),
        "Ueberstunden": round(ueber_h, 2)
    }
    df_entries = df_entries[df_entries["Datum"] != today]
    df_entries = pd.concat([df_entries, pd.DataFrame([new_today_row])], ignore_index=True).sort_values(by="Datum", ascending=False)
    save_data(df_entries, filename)
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# --- 2. DASHBOARD ---
if not df_entries.empty:
    total_ueberstunden = df_entries["Ueberstunden"].sum()
    formatted_ueberstunden = format_time(total_ueberstunden)
    color = "#4CAF50" if total_ueberstunden >= 0 else "#F44336"
    
    st.markdown(f"<div class='metric-box'>📈 <b>Gesamt-Überstunden:</b><br><span style='font-size:28px; font-weight:bold; color:{color};'>{formatted_ueberstunden}</span></div>", unsafe_allow_html=True)

    with st.expander("📊 Statistiken anzeigen"):
        df_entries['Jahr'] = pd.to_datetime(df_entries['Datum']).dt.year
        urlaub_gen = len(df_entries[(df_entries['Jahr'] == today.year) & (df_entries['Urlaub'] == True)])
        st.write(f"**Urlaub {today.year}:** {urlaub_gen} / {URLAUB_KONTINGENT} Tage genutzt")
        
        df_chart = df_entries.sort_values(by="Datum", ascending=True).copy()
        df_chart["Konto"] = df_chart["Ueberstunden"].cumsum()
        st.line_chart(df_chart.set_index("Datum")["Konto"])

    with st.expander("📜 Historie & Einträge löschen"):
        for index, row in df_entries.iterrows():
            c1, c2 = st.columns([4, 1])
            lbl = "🏖️ Urlaub" if row['Urlaub'] else ("🤒 Krank" if row['Krank'] else f"⏱️ {row['Beginn']}-{row['Ende']}")
            c1.write(f"**{row['Datum']}** | {lbl} | **Saldo:** {format_time(row['Ueberstunden'])}")
            if c2.button("🗑️", key=f"del_{index}"):
                df_entries.drop(index, inplace=True)
                save_data(df_entries, filename)
                st.rerun()

    # --- CSV DOWNLOAD BUTTON FÜR GITHUB ---
    st.download_button(
        label="📥 CSV für GitHub herunterladen",
        data=df_entries.to_csv(index=False).encode('utf-8'),
        file_name=filename,
        mime='text/csv',
    )

# --- 3. SIDEBAR: NACHTRAG VERGANGENER TAGE ---
st.sidebar.header("⚙️ Vergangene Tage nachtragen")
all_dates = df_entries[df_entries["Datum"] != today]["Datum"].tolist() if not df_entries.empty else []
mode = st.sidebar.radio("Aktion:", ["Neues Datum eintragen", "Bestehendes Datum anpassen"])

past_date = st.sidebar.date_input("Datum wählen:", today - datetime.timedelta(days=1), max_value=today)
p_start, p_end, p_pause = datetime.time(8, 0), datetime.time(16, 30), 30
p_sick, p_vac, p_week = False, False, False

if mode == "Bestehendes Datum anpassen" and all_dates:
    past_date = st.sidebar.selectbox("Datum auswählen:", all_dates)
    row = df_entries[df_entries["Datum"] == past_date].iloc[0]
    p_sick, p_vac, p_week = bool(row["Krank"]), bool(row["Urlaub"]), bool(row["Wochenende"])
    if not (p_sick or p_vac):
        try: p_start = datetime.datetime.strptime(str(row["Beginn"]), "%H:%M").time()
        except: pass
        try: p_end = datetime.datetime.strptime(str(row["Ende"]), "%H:%M").time()
        except: pass
        p_pause = int(row["Pause_Min"])

p_sick = st.sidebar.checkbox("Krank", value=p_sick, key="p_s")
p_vac = st.sidebar.checkbox("Urlaub", value=p_vac, key="p_v")
p_week = st.sidebar.checkbox("Wochenende", value=p_week, key="p_w")

if not (p_sick or p_vac):
    p_start = st.sidebar.time_input("Beginn:", value=p_start, key="p_start")
    p_end = st.sidebar.time_input("Ende:", value=p_end, key="p_end")
    p_pause = st.sidebar.number_input("Pause (Min):", 0, 120, value=p_pause, step=5, key="p_pause")

if st.sidebar.button("Nachtragen / Ändern"):
    if p_sick or p_vac:
        p_ist, p_soll = 0.0, 0.0
    else:
        diff_s = (datetime.datetime.combine(past_date, p_end) - datetime.datetime.combine(past_date, p_start)).total_seconds()
        if diff_s < 0: diff_s += 86400
        p_ist = (diff_s / 3600) - (p_pause / 60)
        p_soll = 0.0 if p_week else SOLL_STUNDEN_PRO_TAG
    
    new_past_row = {
        "Datum": past_date,
        "Beginn": "Frei" if (p_sick or p_vac) else p_start.strftime("%H:%M"),
        "Ende": "Frei" if (p_sick or p_vac) else p_end.strftime("%H:%M"),
        "Pause_Min": p_pause,
        "Krank": p_sick,
        "Urlaub": p_vac,
        "Wochenende": p_week,
        "Ist_Stunden": round(p_ist, 2),
        "Soll_Stunden": round(p_soll, 2),
        "Ueberstunden": round(p_ist - p_soll, 2)
    }
    df_entries = df_entries[df_entries["Datum"] != past_date]
    df_entries = pd.concat([df_entries, pd.DataFrame([new_past_row])], ignore_index=True).sort_values(by="Datum", ascending=False)
    save_data(df_entries, filename)
    st.rerun()