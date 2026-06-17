import streamlit as st
import pandas as pd
import datetime
import os

# --- SEITEN-KONFIGURATION (Optimiert für Smartphones) ---
st.set_page_config(page_title="ZeitTracker", page_icon="⏱️", layout="centered")

st.title("⏱️ Arbeitszeit-Tracker")
st.write("Erfasse deine Zeiten und behalte deine Überstunden im Blick.")

# --- USER-ISOLATION (Speicher-Strategie) ---
# Dynamischer Typ: 'user_input' wird ein String (str)
username = st.text_input("Dein Nutzername (für deine eigene Datei):", value="Gast").strip().lower()
filename = f"{username}_worklog.csv"

# Festgelegte Soll-Arbeitszeit pro regulärem Arbeitstag (Gleitkommazahl / float)
SOLL_STUNDEN_PRO_TAG = 8.0

# --- FUNKTIONEN ZUM LADEN & SPEICHERN ---
def load_data(file):
    if os.path.exists(file):
        df = pd.read_csv(file)
        # Typkonvertierung: Spalten von Text (str) in echte Datums-Objekte umwandeln
        df['Datum'] = pd.to_datetime(df['Datum']).dt.date
        return df
    else:
        # Falls keine Datei existiert, leere Matrix (DataFrame) mit Struktur erzeugen
        return pd.DataFrame(columns=["Datum", "Beginn", "Ende", "Pause_Min", "Krank", "Wochenende", "Ist_Stunden", "Soll_Stunden", "Ueberstunden"])

def save_data(df, file):
    df.to_csv(file, index=False)

# Daten laden basierend auf dem aktuellen Nutzernamen
df_entries = load_data(filename)

# --- 1. EINGABEMASKE (ZEITERFASSUNG) ---
st.header("📝 Neuen Tag erfassen")

# Datums- und Zeitauswahl liefern native Python-Objekte: datetime.date und datetime.time
selected_date = st.date_input("Datum:", datetime.date.today())
start_time = st.time_input("Arbeitsbeginn:", datetime.time(8, 0))
end_time = st.time_input("Arbeitsende:", datetime.time(16, 30))
break_mins = st.number_input("Pause (in Minuten):", min_value=0, value=30, step=5)

# Status-Flags (Booleans: True / False)
is_sick = st.checkbox("Krankheitstag (Keine Minusstunden)")
is_weekend = st.checkbox("Wochenendarbeit")

if st.button("Eintrag speichern"):
    # Logische Weiche für Sonderfälle
    if is_sick:
        ist_stunden = 0.0
        soll_stunden = 0.0  # Mathematisch neutral: 0 - 0 = 0 Überstunden
    elif is_weekend:
        # Zeitberechnung mittels Kombination von Datum + Uhrzeit
        dt_start = datetime.datetime.combine(selected_date, start_time)
        dt_end = datetime.datetime.combine(selected_date, end_time)
        
        # Berechnung des Differenz-Vektors (timedelta)
        time_diff = dt_end - dt_start
        ist_stunden = (time_diff.total_seconds() / 3600) - (break_mins / 60)
        soll_stunden = 0.0  # Am Wochenende ist regulär 0 Std. Soll -> Alles sind Überstunden
    else:
        dt_start = datetime.datetime.combine(selected_date, start_time)
        dt_end = datetime.datetime.combine(selected_date, end_time)
        
        if dt_end <= dt_start:
            st.error("Fehler: Das Arbeitsende muss nach dem Arbeitsbeginn liegen!")
            ist_stunden = -1.0
        else:
            time_diff = dt_end - dt_start
            ist_stunden = (time_diff.total_seconds() / 3600) - (break_mins / 60)
            soll_stunden = SOLL_STUNDEN_PRO_TAG

    if ist_stunden >= 0.0 or is_sick:
        # Berechnung der Überstundendifferenz (Delta)
        ueberstunden = ist_stunden - soll_stunden
        
        # Neuen Datenpunkt als Dictionary (Assoziatives Array) vorbereiten
        new_row = {
            "Datum": selected_date,
            "Beginn": "Krank" if is_sick else start_time.strftime("%H:%M"),
            "Ende": "Krank" if is_sick else end_time.strftime("%H:%M"),
            "Pause_Min": break_mins if not is_sick else 0,
            "Krank": is_sick,
            "Wochenende": is_weekend,
            "Ist_Stunden": round(ist_stunden, 2),
            "Soll_Stunden": round(soll_stunden, 2),
            "Ueberstunden": round(ueberstunden, 2)
        }
        
        # Bestehende Tabelle filtern, um doppelte Einträge am selben Tag zu überschreiben
        if not df_entries.empty:
            df_entries = df_entries[df_entries["Datum"] != selected_date]
            
        # Aggregation: Zeile an den DataFrame anhängen
        df_entries = pd.concat([df_entries, pd.DataFrame([new_row])], ignore_index=True)
        # Sortierung nach Datum (chronologisch)
        df_entries = df_entries.sort_values(by="Datum", ascending=False)
        
        save_data(df_entries, filename)
        st.success(f"Eintrag für den {selected_date.strftime('%d.%m.%Y')} erfolgreich gespeichert!")
        st.rerun()

# --- 2. DASHBOARDS & STATISTIKEN ---
st.header("📊 Auswertungen")

if not df_entries.empty:
    # Aggoradierte Kennzahlen berechnen (Skalare Reduktion aus Vektoren)
    total_ist = df_entries["Ist_Stunden"].sum()
    total_ueberstunden = df_entries["Ueberstunden"].sum()
    
    # Heutiges Datum für Filterung nutzen
    today = datetime.date.today()
    current_year = today.year
    current_month = today.month
    # ISO-Woche extrahieren
    current_week = today.isocalendar()[1]
    
    # Hilfs-Spalten für zeitliche Gruppierung erzeugen
    df_entries['Jahr'] = pd.to_datetime(df_entries['Datum']).dt.year
    df_entries['Monat'] = pd.to_datetime(df_entries['Datum']).dt.month
    df_entries['Woche'] = pd.to_datetime(df_entries['Datum']).dt.isocalendar().week
    
    # Teilmengen filtern (Slicing)
    df_monat = df_entries[(df_entries['Jahr'] == current_year) & (df_entries['Monat'] == current_month)]
    df_woche = df_entries[(df_entries['Jahr'] == current_year) & (df_entries['Woche'] == current_week)]
    
    st.subheader("Gesamt-Konto")
    st.metric(label="Gearbeitete Stunden Gesamt", value=f"{total_ist:.2f} Std.")
    st.metric(label="Überstunden-Saldo", value=f"{total_ueberstunden:+.2f} Std.", delta=f"{total_ueberstunden:.2f}")

    st.subheader("Aktueller Monat & Aktuelle Woche")
    st.write(f"**Monatsstunden ({current_month}/{current_year}):** {df_monat['Ist_Stunden'].sum():.2f} Std. (Überstunden: {df_monat['Ueberstunden'].sum():+.2f} Std.)")
    st.write(f"**Wochenstunden (KW {current_week}):** {df_woche['Ist_Stunden'].sum():.2f} Std. / Soll: {df_woche['Soll_Stunden'].sum():.2f} Std.")
    
    # --- 3. HISTORIE & LÖSCHFUNKTION ---
    st.header("📜 Verlauf & Verwaltung")
    
    # Wir zeigen dem Nutzer eine Liste mit Löschknöpfen pro Zeile
    for index, row in df_entries.iterrows():
        status_text = ""
        if row['Krank']: status_text = "🤒 Krank"
        elif row['Wochenende']: status_text = "📅 Wochenende"
        else: status_text = f"⏱️ {row['Beginn']} - {row['Ende']} (Pause: {row['Pause_Min']}m)"
        
        # Erstellt ein kompaktes Zeilen-Layout für Smartphones
        col1, col2 = st.columns([4, 1])
        col1.write(f"**{row['Datum'].strftime('%d.%m.%Y')}**: {status_text} | **Netto:** {row['Ist_Stunden']}h | **Überstunden:** {row['Ueberstunden']:+.2f}h")
        
        if col2.button("🗑️", key=f"del_{index}"):
            df_entries = df_entries.drop(index)
            save_data(df_entries, filename)
            st.rerun()
else:
    st.info("Noch keine Einträge für diesen Nutzer vorhanden. Gib oben deinen ersten Tag ein!")