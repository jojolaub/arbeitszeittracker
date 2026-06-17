import streamlit as st
import pandas as pd
import datetime
import os

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Arbeitszeit", page_icon="⏱️", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div.stButton > button:first-child {
        background-color: #4CAF50; color: white; border-radius: 10px;
        border: none; padding: 10px 24px; font-weight: bold; width: 100%;
    }
    .metric-box {
        background-color: white; padding: 15px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⏱️ Arbeitszeit")

username = st.text_input("Nutzername:", value="Gast").strip().lower()
filename = f"{username}_worklog.csv"
SOLL_STUNDEN_PRO_TAG = 8.0
URLAUB_KONTINGENT = 30  # Jahresurlaub

def load_data(file):
    if os.path.exists(file):
        df = pd.read_csv(file)
        df['Datum'] = pd.to_datetime(df['Datum']).dt.date
        # --- DATEN-MIGRATION ---
        # Falls die alte Datei geladen wird, fügen wir die neue Urlaubs-Spalte hinzu
        if 'Urlaub' not in df.columns:
            df['Urlaub'] = False
        return df
    return pd.DataFrame(columns=["Datum", "Beginn", "Ende", "Pause_Min", "Krank", "Urlaub", "Wochenende", "Ist_Stunden", "Soll_Stunden", "Ueberstunden"])

def save_data(df, file):
    df.to_csv(file, index=False)

df_entries = load_data(filename)

# --- BEARBEITUNGS-MODUS ---
st.sidebar.header("⚙️ Eintrag bearbeiten")

all_dates = df_entries["Datum"].tolist() if not df_entries.empty else []
mode = st.sidebar.radio("Modus:", ["Neu anlegen", "Bestehendes anpassen"])

selected_date = datetime.date.today()
default_start, default_end, default_pause = datetime.time(8, 0), datetime.time(16, 30), 30
default_sick, default_vacation, default_weekend = False, False, False

if mode == "Bestehendes anpassen" and all_dates:
    edit_date = st.sidebar.selectbox("Welches Datum anpassen?", all_dates)
    row = df_entries[df_entries["Datum"] == edit_date].iloc[0]
    selected_date = edit_date
    default_sick = bool(row["Krank"])
    default_vacation = bool(row["Urlaub"])
    default_weekend = bool(row["Wochenende"])
    
    if not (default_sick or default_vacation):
        try:
            default_start = datetime.datetime.strptime(row["Beginn"], "%H:%M").time()
            default_end = datetime.datetime.strptime(row["Ende"], "%H:%M").time()
        except:
            pass
        default_pause = int(row["Pause_Min"])

input_date = st.sidebar.date_input("Datum:", selected_date, disabled=(mode == "Bestehendes anpassen"))
is_sick = st.sidebar.checkbox("Krankheitstag", value=default_sick)
is_vacation = st.sidebar.checkbox("Urlaubstag", value=default_vacation)
is_weekend = st.sidebar.checkbox("Wochenendarbeit", value=default_weekend)

if not (is_sick or is_vacation):
    start_time = st.sidebar.time_input("Beginn:", default_start)
    end_time = st.sidebar.time_input("Ende:", default_end)
    # Feature 1: Slider für Pausen (0 bis 90 Minuten in 5er Schritten)
    break_mins = st.sidebar.slider("Pause (Minuten):", min_value=0, max_value=90, value=default_pause, step=5)
else:
    start_time, end_time, break_mins = datetime.time(0,0), datetime.time(0,0), 0

if st.sidebar.button("Änderung / Eintrag speichern"):
    if is_sick or is_vacation:
        ist_stunden, soll_stunden = 0.0, 0.0
    else:
        dt_start = datetime.datetime.combine(input_date, start_time)
        dt_end = datetime.datetime.combine(input_date, end_time)
        faktor = 1.5 if (is_weekend and input_date.weekday() == 6) else 1.0
        
        time_diff = dt_end - dt_start
        ist_stunden = ((time_diff.total_seconds() / 3600) - (break_mins / 60)) * faktor
        soll_stunden = 0.0 if is_weekend else SOLL_STUNDEN_PRO_TAG

    ueberstunden = ist_stunden - soll_stunden
    
    new_row = {
        "Datum": input_date,
        "Beginn": "Frei" if (is_sick or is_vacation) else start_time.strftime("%H:%M"),
        "Ende": "Frei" if (is_sick or is_vacation) else end_time.strftime("%H:%M"),
        "Pause_Min": break_mins,
        "Krank": is_sick,
        "Urlaub": is_vacation,
        "Wochenende": is_weekend,
        "Ist_Stunden": round(ist_stunden, 2),
        "Soll_Stunden": round(soll_stunden, 2),
        "Ueberstunden": round(ueberstunden, 2)
    }
    
    if not df_entries.empty:
        df_entries = df_entries[df_entries["Datum"] != input_date]
        
    df_entries = pd.concat([df_entries, pd.DataFrame([new_row])], ignore_index=True)
    df_entries = df_entries.sort_values(by="Datum", ascending=False)
    save_data(df_entries, filename)
    st.success("Erfolgreich aktualisiert!")
    st.rerun()

# --- DASHBOARD & STATISTIKEN ---
if not df_entries.empty:
    total_ist = df_entries["Ist_Stunden"].sum()
    total_ueberstunden = df_entries["Ueberstunden"].sum()
    
    # Feature 3: Urlaubsberechnung (Zählung der Wahrheitswerte 'True' für aktuelles Jahr)
    today = datetime.date.today()
    df_entries['Jahr'] = pd.to_datetime(df_entries['Datum']).dt.year
    df_entries['Monat'] = pd.to_datetime(df_entries['Datum']).dt.month
    df_entries['Woche'] = pd.to_datetime(df_entries['Datum']).dt.isocalendar().week
    
    urlaub_genommen = len(df_entries[(df_entries['Jahr'] == today.year) & (df_entries['Urlaub'] == True)])
    urlaub_uebrig = URLAUB_KONTINGENT - urlaub_genommen
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-box'>🎒 <b>Ist-Stunden</b><br><span style='font-size:18px; font-weight:bold;'>{total_ist:.2f}</span></div>", unsafe_allow_html=True)
    with col2:
        color = "#4CAF50" if total_ueberstunden >= 0 else "#F44336"
        st.markdown(f"<div class='metric-box'>📈 <b>Überstunden</b><br><span style='font-size:18px; font-weight:bold; color:{color};'>{total_ueberstunden:+.2f}</span></div>", unsafe_allow_html=True)
    with col3:
        color_u = "#F44336" if urlaub_uebrig < 5 else "#4CAF50"
        st.markdown(f"<div class='metric-box'>🏖️ <b>Urlaub übrig</b><br><span style='font-size:18px; font-weight:bold; color:{color_u};'>{urlaub_uebrig} Tage</span></div>", unsafe_allow_html=True)

    # Feature 2: Grafische Visualisierung (Letzte 4 Wochen)
    st.subheader("📈 Überstunden-Verlauf (Letzte 4 Wochen)")
    
    # Für einen korrekten Graphen sortieren wir chronologisch aufsteigend
    df_chart = df_entries.sort_values(by="Datum", ascending=True).copy()
    # Kumulierte Summe berechnen
    df_chart["Konto_Stand"] = df_chart["Ueberstunden"].cumsum()
    
    # Filter für die letzten 28 Tage
    four_weeks_ago = today - datetime.timedelta(days=28)
    df_filtered = df_chart[df_chart["Datum"] >= four_weeks_ago]
    
    if not df_filtered.empty:
        # Index auf Datum setzen, damit st.line_chart die X-Achse korrekt beschriftet
        df_filtered.set_index("Datum", inplace=True)
        st.line_chart(df_filtered["Konto_Stand"])
    else:
        st.info("Noch nicht genug Daten aus den letzten 4 Wochen für ein Diagramm.")
    
    # VERLAUF LISTE
    st.subheader("📜 Verlauf")
    for index, row in df_entries.iterrows():
        with st.container():
            c1, c2 = st.columns([4, 1])
            lbl = "🏖️ Urlaub" if row.get('Urlaub', False) else ("🤒 Krank" if row['Krank'] else ("📅 Wochenende" if row['Wochenende'] else f"⏱️ {row['Beginn']}-{row['Ende']}"))
            c1.write(f"**{row['Datum'].strftime('%d.%m.%Y')}** | {lbl} | **Überstunden:** {row['Ueberstunden']:+.2f}h")
            if c2.button("🗑️", key=f"del_{index}"):
                df_entries = df_entries.drop(index)
                save_data(df_entries, filename)
                st.rerun()
else:
    st.info("Keine Daten vorhanden. Nutze die Seitenleiste links zum Hinzufügen!")