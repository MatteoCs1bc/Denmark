import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configurazione pagina
st.set_page_config(page_title="Analisi Rete Elettrica Danese", layout="wide")

st.title("⚡ Analisi Rete Danimarca: Intermittenza e Generazione")
st.markdown("Questa dashboard analizza i dati orari di Energinet per visualizzare il mix energetico, la penetrazione delle rinnovabili intermittenti e il ruolo del gas come backup.")

@st.cache_data
def load_data():
    # Carica il dataset principale
    # Usa decimal=',' per gestire i numeri europei
    df = pd.read_csv("GenerationProdTypeExchange.csv", sep=";", decimal=",")
    df['TimeDK'] = pd.to_datetime(df['TimeDK'])
    
    # Somma le due zone di prezzo (DK1 e DK2) per avere il dato nazionale totale per ogni ora
    df_grouped = df.groupby('TimeDK').sum(numeric_only=True).reset_index()
    df_grouped = df_grouped.sort_values('TimeDK')
    return df_grouped

try:
    df = load_data()
except FileNotFoundError:
    st.error("File 'GenerationProdTypeExchange.csv' non trovato. Assicurati che sia nella stessa cartella dello script.")
    st.stop()

# --- SIDEBAR E FILTRI ---
min_date = df['TimeDK'].min().date()
max_date = df['TimeDK'].max().date()

st.sidebar.header("Filtri")
selected_date = st.sidebar.date_input("Seleziona una data", min_date, min_value=min_date, max_value=max_date)

# Filtro i dati per il giorno selezionato
mask = df['TimeDK'].dt.date == selected_date
df_day = df[mask]

if df_day.empty:
    st.warning("Nessun dato disponibile per questa data.")
    st.stop()

# --- KPI PRINCIPALI ---
st.subheader(f"Statistiche della giornata: {selected_date.strftime('%d/%m/%Y')}")

total_gen = df_day[['OffshoreWindPower', 'OnshoreWindPower', 'SolarPower', 'SolarPowerSelfCon', 
                    'HydroPower', 'Biomass', 'Biogas', 'Waste', 'FossilGas', 'FossilOil', 'FossilHardCoal']].sum().sum()
total_load = df_day['GrossCon'].sum()
total_wind_solar = df_day[['OffshoreWindPower', 'OnshoreWindPower', 'SolarPower', 'SolarPowerSelfCon']].sum().sum()

col1, col2, col3 = st.columns(3)
col1.metric("Domanda Lorda (MWh)", f"{total_load:,.0f}")
col2.metric("Generazione Totale (MWh)", f"{total_gen:,.0f}")
col3.metric("Penetrazione Rinnovabili (Vento+Sole)", f"{(total_wind_solar/total_load)*100:.1f}%")

# --- GRAFICO PRINCIPALE: Mix di Generazione (Stack Area) ---
st.subheader("Curva di Generazione per Fonte")

fig = go.Figure()

# Fonti ordinate per "merit order" (dal baseload al picco solare)
sources = {
    'FossilHardCoal': ('Carbone', '#1f1f1f'),
    'FossilOil': ('Olio', '#5c5c5c'),
    'FossilGas': ('Gas Naturale (Turbogas)', '#8c564b'),
    'Waste': ('Rifiuti', '#7f7f7f'),
    'Biogas': ('Biogas', '#2ca02c'),
    'Biomass': ('Biomassa', '#98df8a'),
    'HydroPower': ('Idroelettrico', '#1f77b4'),
    'OffshoreWindPower': ('Eolico Offshore', '#17becf'),
    'OnshoreWindPower': ('Eolico Onshore', '#9edae5'),
    'SolarPower': ('Fotovoltaico (Rete)', '#ff7f0e'),
    'SolarPowerSelfCon': ('Fotovoltaico (Autoconsumo)', '#ffbb78')
}

for col_name, (label, color) in sources.items():
    if col_name in df_day.columns and df_day[col_name].sum() > 0:
        fig.add_trace(go.Scatter(
            x=df_day['TimeDK'],
            y=df_day[col_name],
            name=label,
            mode='lines',
            line=dict(width=0, color=color),
            stackgroup='one' # Effetto area impilata (stacked area)
        ))

# Aggiungo la linea della domanda elettrica
fig.add_trace(go.Scatter(
    x=df_day['TimeDK'],
    y=df_day['GrossCon'],
    name='Domanda Lorda',
    mode='lines',
    line=dict(color='black', width=3, dash='dash')
))

fig.update_layout(
    xaxis_title="Ora del giorno",
    yaxis_title="Produzione (MWh)",
    hovermode="x unified",
    legend_title="Fonti",
    height=600,
    margin=dict(l=0, r=0, t=30, b=0)
)

st.plotly_chart(fig, use_container_width=True)

# --- GRAFICO 2: Interscambio (Import/Export) ---
st.subheader("Interscambio Estero (Bilanciamento della Rete)")
st.markdown("*Valori positivi = Importazione (manca energia). Valori negativi = Esportazione (eccesso di rinnovabili).*")

fig_exc = go.Figure()
exchanges = {
    'ExchangeGermany': ('Germania', '#d62728'),
    'ExchangeSweden': ('Svezia', '#2ca02c'),
    'ExchangeNorway': ('Norvegia', '#1f77b4'),
    'ExchangeNetherlands': ('Paesi Bassi', '#ff7f0e'),
    'ExchangeGreatBritain': ('Gran Bretagna', '#9467bd')
}

for col_name, (label, color) in exchanges.items():
    if col_name in df_day.columns and df_day[col_name].abs().sum() > 0:
        fig_exc.add_trace(go.Scatter(
            x=df_day['TimeDK'],
            y=df_day[col_name],
            name=label,
            mode='lines',
            line=dict(width=2, color=color)
        ))

fig_exc.update_layout(
    xaxis_title="Ora del giorno",
    yaxis_title="Interscambio (MWh)",
    hovermode="x unified",
    height=400
)
st.plotly_chart(fig_exc, use_container_width=True)
