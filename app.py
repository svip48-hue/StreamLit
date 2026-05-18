import requests
import pandas as pd
from io import StringIO
import json
import geopandas as gpd
import matplotlib.pyplot as plt
import streamlit as st

STATISTIKAAMETI_API_URL = "https://andmed.stat.ee/api/v1/et/stat/RV032"

JSON_PAYLOAD_STR = """
{
  "query": [
    {
      "code": "Aasta",
      "selection": {
        "filter": "item",
        "values": ["2014","2015","2016","2017","2018","2019","2020","2021","2022","2023"]
      }
    },
    {
      "code": "Maakond",
      "selection": {
        "filter": "item",
        "values": ["39","44","49","51","57","59","65","67","70","74","78","82","84","86","37"]
      }
    },
    {
      "code": "Sugu",
      "selection": {
        "filter": "item",
        "values": ["2","3"]
      }
    }
  ],
  "response": {
    "format": "csv"
  }
}
"""

GEOJSON_PATH = "maakonnad.geojson"


@st.cache_data
def import_data():
    headers = {'Content-Type': 'application/json'}
    parsed_payload = json.loads(JSON_PAYLOAD_STR)
    response = requests.post(STATISTIKAAMETI_API_URL, json=parsed_payload, headers=headers)

    if response.status_code == 200:
        text = response.content.decode('utf-8-sig')
        df = pd.read_csv(StringIO(text))
        return df
    else:
        st.error(f"Andmete laadimine ebaõnnestus: {response.status_code}")
        return None


@st.cache_data
def import_geojson():
    gdf = gpd.read_file(GEOJSON_PATH)
    return gdf


def prepare_data(df, gdf):
    merged = gdf.merge(df, left_on='MNIMI', right_on='Maakond')
    merged["Loomulik iive"] = merged["Mehed Loomulik iive"] + merged["Naised Loomulik iive"]
    return merged


def plot_map(df, year):
    year_data = df[df.Aasta == year]

    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    year_data.plot(
        column='Loomulik iive',
        ax=ax,
        legend=True,
        cmap='RdYlGn',
        legend_kwds={'label': "Loomulik iive (inimest)"},
        edgecolor='white',
        linewidth=0.5
    )
    plt.title(f'Loomulik iive maakonniti aastal {year}', fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    return fig


# ── Streamlit UI ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Loomulik iive Eestis", page_icon="🗺️", layout="wide")

st.title("🗺️ Loomulik iive Eesti maakondades")
st.markdown("Andmed: [Statistikaamet RV032](https://andmed.stat.ee/et/stat/RV032)")

with st.spinner("Laadin andmeid..."):
    df = import_data()
    gdf = import_geojson()

if df is not None and gdf is not None:
    merged = prepare_data(df, gdf)

    years = sorted(merged["Aasta"].unique(), reverse=True)

    # Sidebar
    st.sidebar.header("⚙️ Seaded")
    selected_year = st.sidebar.selectbox("Vali aasta:", years)

    # Stats
    year_data = merged[merged.Aasta == selected_year]
    col1, col2, col3 = st.columns(3)
    col1.metric("📅 Aasta", selected_year)
    col2.metric("📉 Min iive", f"{int(year_data['Loomulik iive'].min())} ({year_data.loc[year_data['Loomulik iive'].idxmin(), 'Maakond']})")
    col3.metric("📈 Max iive", f"{int(year_data['Loomulik iive'].max())} ({year_data.loc[year_data['Loomulik iive'].idxmax(), 'Maakond']})")

    # Map
    fig = plot_map(merged, selected_year)
    st.pyplot(fig)

    # Table
    with st.expander("📊 Vaata andmeid tabelina"):
        table = year_data[["Maakond", "Loomulik iive"]].sort_values("Loomulik iive").reset_index(drop=True)
        st.dataframe(table, use_container_width=True)
