import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configurazione pagina
st.set_page_config(page_title="Analisi Rete Danese V2", layout="wide")

st.title("⚡ Analisi Rete Danimarca: Intermittenza, Capacità e Storage")

# --- DATI STATICI: POTENZA INSTALLATA (GW) ---
# Dati approssimativi Danimarca (aggiornati al 2023/2024)
# Poiché il file CSV contiene solo la generazione, usiamo un dizionario statico
# I valori sono in MW (Megawatt)
CAPACITY_MW = {
    'OnshoreWindPower': 4800,
    'OffshoreWindPower': 2700,
    'SolarPower_Total': 3500, # Somma di rete e autoconsumo
    'FossilGas': 1500, # Capacità termica flessibile
}

@st.cache_data
def load_data():
    df = pd.read_csv("GenerationProdTypeExchange.csv", sep=";", decimal=",")
    df['TimeDK'] = pd.to_datetime(df['TimeDK'])
    df_grouped = df.groupby('TimeDK').sum(numeric_only=True).reset_index()
    df_grouped = df_grouped.sort_values('TimeDK')
    
    # Creiamo una colonna aggregata per il solare totale per comodità
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

# --- SEZIONE 1: BATTERIE E STORAGE ---
st.info("🔋 **Il ruolo delle Batterie in Danimarca:** Nel dataset principale di Energinet non è presente una colonna dedicata all'accumulo a batterie (BESS). Questo perché la Danimarca utilizza storicamente i **cavi di interconnessione con Norvegia e Svezia come un'immensa batteria virtuale** (sfruttando il loro idroelettrico a pompaggio). Le batterie domestiche/utility-scale stanno crescendo, ma sono usate perlopiù per i servizi di dispacciamento ultra-rapidi (FCR), non per lo shift di grandi volumi di energia (arbitraggio).")

# --- SEZIONE 2: KPI E CAPACITA' INSTALLATA ---
st.subheader(f"Resa Impianti (Capacity Factor) - {selected_date.strftime('%d/%m/%Y')}")

# Calcoliamo il picco massimo di generazione raggiunto in quel giorno
max_solar = df_day['SolarPower_Total'].max()
max_onshore = df_day['OnshoreWindPower'].max()
max_offshore = df_day['OffshoreWindPower'].max()

col1, col2, col3 = st.columns(3)

col1.metric(
    "Fotovoltaico (Picco vs Installato)", 
    f"{max_solar:,.0f} MW", 
    f"{(max_solar/CAPACITY_MW['SolarPower_Total'])*100:.1f}% della capacità",
    delta_color="off"
)
col2.metric(
    "Eolico Onshore (Picco vs Installato)", 
    f"{max_onshore:,.0f} MW", 
    f"{(max_onshore/CAPACITY_MW['OnshoreWindPower'])*100:.1f}% della capacità",
    delta_color="off"
)
col3.metric(
    "Eolico Offshore (Picco vs Installato)", 
    f"{max_offshore:,.0f} MW", 
    f"{(max_offshore/CAPACITY_MW['OffshoreWindPower'])*100:.1f}% della capacità",
    delta_color="off"
)


# --- GRAFICO PRINCIPALE: Mix di Generazione (Stack Area) ---
st.subheader("Curva di Generazione per Fonte")
fig = go.Figure()

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

# Se nel dataset futuro aggiungessi le batterie:
if 'BatteryDischarge' in df_day.columns:
    sources['BatteryDischarge'] = ('Scarica Batterie', '#e377c2')

for col_name, (label, color) in sources.items():
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
