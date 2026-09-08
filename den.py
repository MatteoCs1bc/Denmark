import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configurazione pagina
st.set_page_config(page_title="Analisi Rete Danese V3", layout="wide")

st.title("⚡ Analisi Rete Danimarca: Intermittenza e Capacità Installata")

# --- DATI STATICI: POTENZA INSTALLATA (MW) ---
# Dati approssimativi del parco di generazione danese
CAPACITY_MW = {
    'OnshoreWindPower': {'label': 'Eolico Onshore', 'mw': 4800, 'color': '#9edae5'},
    'SolarPower_Total': {'label': 'Fotovoltaico (Totale)', 'mw': 4000, 'color': '#ff7f0e'},
    'OffshoreWindPower': {'label': 'Eolico Offshore', 'mw': 2700, 'color': '#17becf'},
    'Biomass': {'label': 'Biomassa', 'mw': 2000, 'color': '#98df8a'},
    'FossilGas': {'label': 'Gas Naturale', 'mw': 1500, 'color': '#8c564b'},
    'FossilHardCoal': {'label': 'Carbone', 'mw': 900, 'color': '#1f1f1f'},
    'Waste': {'label': 'Rifiuti', 'mw': 500, 'color': '#7f7f7f'},
    'FossilOil': {'label': 'Olio Combustibile', 'mw': 400, 'color': '#5c5c5c'},
    'Biogas': {'label': 'Biogas', 'mw': 150, 'color': '#2ca02c'},
    'HydroPower': {'label': 'Idroelettrico', 'mw': 10, 'color': '#1f77b4'},
}

@st.cache_data
def load_data():
    df = pd.read_csv("GenerationProdTypeExchange.csv", sep=";", decimal=",")
    df['TimeDK'] = pd.to_datetime(df['TimeDK'])
    df_grouped = df.groupby('TimeDK').sum(numeric_only=True).reset_index()
    df_grouped = df_grouped.sort_values('TimeDK')
    
    if 'SolarPower' in df_grouped.columns and 'SolarPowerSelfCon' in df_grouped.columns:
        df_grouped['SolarPower_Total'] = df_grouped['SolarPower'] + df_grouped['SolarPowerSelfCon']
        
    return df_grouped

try:
    df = load_data()
except FileNotFoundError:
    st.error("File 'GenerationProdTypeExchange.csv' non trovato.")
    st.stop()

# --- SIDEBAR E FILTRI ---
min_date = df['TimeDK'].min().date()
max_date = df['TimeDK'].max().date()
st.sidebar.header("Filtri")
selected_date = st.sidebar.date_input("Seleziona una data", min_date, min_value=min_date, max_value=max_date)

mask = df['TimeDK'].dt.date == selected_date
df_day = df[mask]

if df_day.empty:
    st.warning("Nessun dato disponibile per questa data.")
    st.stop()


# --- SEZIONE 1: POTENZA INSTALLATA ---
st.subheader("🏗️ Potenza Installata per Fonte (Capacità Nominale)")
st.markdown("Questa sezione mostra la capacità massima teorica installata in Danimarca per ogni tecnologia.")

# Prepariamo i dati per il grafico a barre
cap_df = pd.DataFrame.from_dict(CAPACITY_MW, orient='index').reset_index()
cap_df = cap_df.sort_values(by='mw', ascending=True)

fig_cap = go.Figure(go.Bar(
    x=cap_df['mw'],
    y=cap_df['label'],
    orientation='h',
    marker_color=cap_df['color'],
    text=cap_df['mw'].apply(lambda x: f"{x:,.0f} MW"),
    textposition='auto'
))
fig_cap.update_layout(
    height=400,
    xaxis_title="Potenza Installata (MW)",
    margin=dict(l=0, r=0, t=10, b=0)
)
st.plotly_chart(fig_cap, use_container_width=True)


# --- GRAFICO PRINCIPALE: Mix di Generazione (Stack Area) ---
st.subheader(f"📈 Curva di Generazione Reale - {selected_date.strftime('%d/%m/%Y')}")

fig = go.Figure()

sources_gen = {
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

for col_name, (label, color) in sources_gen.items():
    if col_name in df_day.columns and df_day[col_name].sum() > 0:
        fig.add_trace(go.Scatter(
            x=df_day['TimeDK'], y=df_day[col_name], name=label,
            mode='lines', line=dict(width=0, color=color), stackgroup='one'
        ))

fig.add_trace(go.Scatter(
    x=df_day['TimeDK'], y=df_day['GrossCon'], name='Domanda Lorda',
    mode='lines', line=dict(color='black', width=3, dash='dash')
))

fig.update_layout(xaxis_title="Ora", yaxis_title="Produzione (MW)", hovermode="x unified", height=600)
st.plotly_chart(fig, use_container_width=True)
