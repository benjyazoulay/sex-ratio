import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen
from branca.colormap import LinearColormap
from streamlit_folium import st_folium

# Configuration de la page Streamlit pour utiliser toute la largeur
st.set_page_config(layout="wide")

# Suppression des marges par défaut de Streamlit
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .element-container {
            margin-bottom: 0.5rem;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Chargement des données
file_path = 'df.csv'
df = pd.read_csv(file_path)

@st.cache_data
def calculer_sex_ratio(df, age_min, age_max):
    hommes_cols = [col for col in df.columns if col.startswith('X1') and age_min <= int(col[2:]) <= age_max]
    femmes_cols = [col for col in df.columns if col.startswith('X2') and age_min <= int(col[2:]) <= age_max]
    
    df['total_hommes'] = df[hommes_cols].sum(axis=1)
    df['total_femmes'] = df[femmes_cols].sum(axis=1)
    df['total_age_population'] = df['total_hommes'] + df['total_femmes']
    df['H/F'] = (df['total_hommes'] / df['total_femmes']) * 100

    df_filtered = df[df['LIBGEO'] != 'Fleury-Mérogi']
    df_top_300 = df_filtered.nlargest(300, 'total_age_population')
    return df_top_300

# Interface utilisateur dans un conteneur
with st.container():
   
    # Slider dans une colonne plus étroite
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        age_min, age_max = st.slider("Sélectionnez l'intervalle d'âge :", 0, 100, (20, 30))

    # Calculs
    df_filtered = calculer_sex_ratio(df, age_min, age_max)
    pop_min = df_filtered['total_age_population'].min()
    pop_max = df_filtered['total_age_population'].max()

    # Création de la carte
    m = folium.Map(location=[46.603354, 1.888334], zoom_start=6, tiles='cartodb positron', control_scale=True)
    Fullscreen().add_to(m)

    # Colormap
    colormap = LinearColormap(
        colors=['red', 'white', 'blue'],
        index=[75, 100, 125],
        vmin=75, vmax=125,
        caption='H/F Ratio (Rouge <75, Blanc=100, Bleu >125)'
    )
    colormap.add_to(m)

    # Ajout des cercles
    for idx, row in df_filtered.iterrows():
        radius = 5 + (row['total_age_population'] - pop_min) / (pop_max - pop_min) * 25
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=radius,
            color=colormap(row['H/F']),
            fill=True,
            fill_color=colormap(row['H/F']),
            fill_opacity=0.7,
            popup=f"<strong>{row['LIBGEO']}</strong><br>H/F: {row['H/F']:.2f}<br>Population: {row['total_age_population']}"
        ).add_to(m)

    # Calcul dynamique de la hauteur en fonction de la largeur de l'écran
    width = "100%"
    height = 700

    # Affichage de la carte avec des dimensions responsives
    st_folium(m, width=width, height=height, returned_objects=[])
    
    # Source en petit et collée à la carte
    st.markdown("<div style='margin-top: -1rem; font-size: 0.8em;'>Source INSEE 2021</div>", unsafe_allow_html=True)