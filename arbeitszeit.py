import streamlit as st
import pandas as pd
import datetime
import os

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Arbeitszeit", page_icon="⏱️", layout="centered")

st.markdown("""
    <style>
    .metric-box { background-color: #f0f2f6; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("⏱️ Arbeitszeit")

# Voreinstellung auf jojo
username = st.text_input("Nutzername:", value="jojo").strip().lower()
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

df_entries = load_data(filename)

# --- SIDEBAR (Eingabe) ---
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
    default_sick, default_vacation, default_weekend = bool(row["Krank"]), bool(row["Urlaub"]), bool(row["Wochenende"])
    if not (default_sick or default_vacation):
        try:
            default_start = datetime.datetime.strptime(str(row["Beginn"]), "%H:%M").time()
            default_end = datetime.datetime.strptime(str(row["Ende"]), "%H:%M").time()
        except: pass
        default_pause = int(row["Pause_Min"])

input_date = st.sidebar.date_input("Datum:", selected_date, disabled=(mode == "Bestehendes anpassen"))
is_sick = st.sidebar.checkbox("Krankheitstag", value=default_sick)
is_vacation = st.sidebar.checkbox("Urlaubstag", value=default_vacation)
is_weekend = st.sidebar.checkbox("Wochenendarbeit", value=default_weekend)

if not (is_sick or is_vacation):
    start_time = st.sidebar.time_input("Beginn:", default_start)
    end_time = st.sidebar.time_input("Ende:", default_end)
    break_mins = st.sidebar.slider("Pause (Minuten):", 0, 90, default_pause, step=5)
else:
    start_time, end_time, break_mins = datetime.time(0,0), datetime.time(0,0), 0

if st.sidebar.button("Speichern"):
    ist_stunden = 0.0 if (is_sick or is_vacation) else ((datetime.datetime.combine(input_date, end_time) - datetime.datetime.combine(input_date, start_time)).total_seconds() / 3600) - (break_mins / 60)
    # Wochenendarbeit: Soll-Stunden sind 0, da es Überstunden-Zeit ist
    soll_stunden = 0.0 if (is_weekend or is_sick or is_vacation) else SOLL_STUNDEN_PRO_TAG
    new_row = {"Datum": input_date, "Beginn": "Frei" if (is_sick or is_vacation) else start_time.strftime("%H:%M"), "Ende": "Frei" if (is_sick or is_vacation) else end_time.strftime("%H:%M"), "Pause_Min": break_mins, "Krank": is_sick, "Urlaub": is_vacation, "Wochenende": is_weekend, "Ist_Stunden": round(ist_stunden, 2), "Soll_Stunden": round(soll_stunden, 2), "Ueberstunden": round(ist_stunden - soll_stunden, 2)}
    df_entries = pd.concat([df_entries[df_entries["Datum"] != input_date], pd.DataFrame([new_row])], ignore_index=True).sort_values(by="Datum", ascending=False)
    save_data(df_entries, filename)
    st.rerun()

# --- DASHBOARD ---
if not df_entries.empty:
    total_ueberstunden = df_entries["Ueberstunden"].sum()
    st.markdown(f"<div class='metric-box'>📈 <b>Gesamt-Überstunden:</b><br><span style='font-size:24px; font-weight:bold; color:{('#4CAF50' if total_ueberstunden >= 0 else '#F44336')};'>{total_ueberstunden:+.2f} Std.</span></div>", unsafe_allow_html=True)

    with st.expander("📊 Statistiken anzeigen"):
        df_entries['Jahr'] = pd.to_datetime(df_entries['Datum']).dt.year
        urlaub_gen = len(df_entries[(df_entries['Jahr'] == datetime.date.today().year) & (df_entries['Urlaub'] == True)])
        st.write(f"**Urlaub dieses Jahr:** {urlaub_gen} / {URLAUB_KONTINGENT} Tage genutzt")
        df_chart = df_entries.sort_values(by="Datum", ascending=True).copy()
        df_chart["Konto"] = df_chart["Ueberstunden"].cumsum()
        st.line_chart(df_chart.set_index("Datum")["Konto"])

    with st.expander("📜 Historie & Bearbeitung"):
        for index, row in df_entries.iterrows():
            c1, c2 = st.columns([4, 1])
            lbl = "🏖️ Urlaub" if row['Urlaub'] else ("🤒 Krank" if row['Krank'] else f"⏱️ {row['Beginn']}-{row['Ende']}")
            c1.write(f"**{row['Datum']}** | {lbl} | **Saldo:** {row['Ueberstunden']:+.2f}h")
            if c2.button("🗑️", key=f"del_{index}"):
                df_entries.drop(index, inplace=True)
                save_data(df_entries, filename)
                st.rerun()