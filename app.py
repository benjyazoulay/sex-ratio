import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen
from branca.colormap import LinearColormap
from streamlit_folium import st_folium
import plotly.graph_objects as go
import numpy as np

# Configuration de la page Streamlit pour utiliser toute la largeur
st.set_page_config(layout="wide",page_title="Mating App",page_icon="❤️")

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

def get_color(ratio):
    """Retourne une couleur RGB basée sur le ratio H/F"""
    if ratio <= 75:
        return 'rgb(255, 0, 0)'  # Rouge
    elif ratio >= 125:
        return 'rgb(0, 0, 255)'  # Bleu
    elif ratio == 100:
        return 'rgb(255, 255, 255)'  # Blanc
    elif ratio < 100:
        # Interpolation entre rouge et blanc
        factor = (ratio - 75) / 25
        return f'rgb({255}, {int(255*factor)}, {int(255*factor)})'
    else:
        # Interpolation entre blanc et bleu
        factor = (ratio - 100) / 25
        return f'rgb({int(255*(1-factor))}, {int(255*(1-factor))}, 255)'

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
    m = folium.Map(location=[46.603354, 1.888334], zoom_start=6, tiles='cartodb dark_matter', control_scale=True)
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
        # Utiliser une échelle logarithmique pour le rayon
        radius = 5 + (np.log(row['total_age_population'] + 1) - np.log(pop_min + 1)) / (np.log(pop_max + 1) - np.log(pop_min + 1)) * 25
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=radius,
            color=colormap(row['H/F']),
            fill=True,
            fill_color=colormap(row['H/F']),
            fill_opacity=0.7,
            popup=f"<strong>{row['LIBGEO']}</strong><br>H/F: {row['H/F']:.2f}<br>Population: {row['total_age_population']}"
        ).add_to(m)


    # Affichage de la carte avec des dimensions responsives
    st_folium(m, width="100%", height=700, returned_objects=[])
    
    # Source en petit et collée à la carte
    st.markdown("<div style='margin-top: -1rem; font-size: 0.8em;'>Source INSEE 2021</div>", unsafe_allow_html=True)

    # Création du barplot horizontal
    df_sorted = df_filtered.sort_values('H/F', ascending=True)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_sorted['LIBGEO'],
        x=df_sorted['H/F'],
        orientation='h',
        marker=dict(
            color=[get_color(ratio) for ratio in df_sorted['H/F']],
            line=dict(width=0)
        ),
        hovertemplate='<b>%{y}</b><br>' +
                      'Ratio H/F: %{x:.1f}<br>' +
                      '<extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text=f"Ratio H/F par ville (population {age_min}-{age_max} ans)",
            x=0.5,
            y=0.98
        ),
        xaxis_title="Ratio H/F",
        yaxis_title="Villes",
        height=800,  # Hauteur fixe pour accommoder toutes les villes
        margin=dict(l=200, r=20, t=40, b=20),  # Marge gauche augmentée pour les noms de villes
        showlegend=False,
        plot_bgcolor='white',
        xaxis=dict(
            gridcolor='lightgray',
            zeroline=True,
            zerolinecolor='black',
            zerolinewidth=1
        )
    )

    # Ajout d'une ligne verticale à 100 (parité)
    fig.add_vline(x=100, line_width=1, line_dash="dash", line_color="black")

    # Affichage du graphique
    st.plotly_chart(fig, use_container_width=True)
