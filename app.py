import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen
from branca.colormap import LinearColormap
from streamlit_folium import st_folium
import plotly.graph_objects as go
import numpy as np

# Configuration de la page Streamlit pour utiliser toute la largeur
st.set_page_config(layout="wide", page_title="Mating App", page_icon="❤️")

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
    # Gestion de la division par zéro si une ville n'a pas de femmes dans la tranche d'âge
    df['H/F'] = np.where(df['total_femmes'] > 0, (df['total_hommes'] / df['total_femmes']) * 100, np.inf)

    df_filtered = df[df['LIBGEO'] != 'Fleury-Mérogi']
    df_top_300 = df_filtered.nlargest(300, 'total_age_population')
    return df_top_300

# MODIFICATION 1: Nouvelle fonction de couleur qui dépend du profil
def get_color_for_profile(ratio, profile):
    """Retourne une couleur RGB basée sur le ratio H/F et le profil de l'utilisateur."""
    # Définition des couleurs : Vert = Favorable, Rouge = Défavorable
    favorable_color = (46, 139, 87)  # Vert SeaGreen
    unfavorable_color = (220, 20, 60) # Rouge Crimson
    mid_color = (255, 255, 255)      # Blanc

    # Normalisation des ratios extrêmes pour la couleur
    if ratio <= 75: ratio = 75
    if ratio >= 125: ratio = 125

    # Logique de couleur inversée selon le profil
    if profile == 'Un homme':
        # Pour un homme, favorable = ratio < 100 (plus de femmes)
        low_color, high_color = favorable_color, unfavorable_color
    else: # Pour une femme, favorable = ratio > 100 (plus d'hommes)
        low_color, high_color = unfavorable_color, favorable_color
    
    if ratio < 100:
        factor = (ratio - 75) / 25
        r = low_color[0] + factor * (mid_color[0] - low_color[0])
        g = low_color[1] + factor * (mid_color[1] - low_color[1])
        b = low_color[2] + factor * (mid_color[2] - low_color[2])
    else:
        factor = (ratio - 100) / 25
        r = mid_color[0] + factor * (high_color[0] - mid_color[0])
        g = mid_color[1] + factor * (high_color[1] - mid_color[1])
        b = mid_color[2] + factor * (high_color[2] - mid_color[2])
        
    return f'rgb({int(r)}, {int(g)}, {int(b)})'

# --- INTERFACE UTILISATEUR ---
with st.container():
    col1, col2 = st.columns([1, 3])
    
    # MODIFICATION 2: Ajout du sélecteur de profil
    with col1:
        st.markdown("**Votre profil**")
        profile = st.radio(
            "Votre profil",
            ('Un homme', 'Une femme'),
            label_visibility="collapsed"
        )

    with col2:
        st.markdown(f"**Tranche d'âge que vous recherchez**")
        age_min, age_max = st.slider(
            "Tranche d'âge que vous recherchez", 
            0, 100, (20, 25), 
            label_visibility="collapsed"
        )

    # Calculs
    df_filtered = calculer_sex_ratio(df, age_min, age_max)
    pop_min = df_filtered['total_age_population'].min()
    pop_max = df_filtered['total_age_population'].max()

    # --- CARTE FOLIUM ---
    m = folium.Map(location=[46.603354, 1.888334], zoom_start=6, control_scale=True)
    Fullscreen().add_to(m)

    # MODIFICATION 3: Colormap dynamique et légende adaptée
    if profile == 'Un homme':
        colors = ['seagreen', 'white', 'crimson']
        caption = 'Score d\'opportunité (Vert: + de femmes, Rouge: + d\'hommes)'
    else:
        colors = ['crimson', 'white', 'seagreen']
        caption = 'Score d\'opportunité (Vert: + d\'hommes, Rouge: + de femmes)'
        
    colormap = LinearColormap(
        colors=colors,
        index=[75, 100, 125],
        vmin=75, vmax=125,
        caption=caption
    )
    colormap.add_to(m)

    # Ajout des cercles (logique inchangée, mais la couleur vient de la nouvelle colormap)
    for idx, row in df_filtered.iterrows():
        radius = 5 + (np.log(row['total_age_population'] + 1) - np.log(pop_min + 1)) / (np.log(pop_max + 1) - np.log(pop_min + 1)) * 25
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=radius,
            color=colormap(row['H/F']),
            fill=True,
            fill_color=colormap(row['H/F']),
            fill_opacity=0.7,
            popup=f"<strong>{row['LIBGEO']}</strong><br>Ratio H/F: {row['H/F']:.2f}<br>Pop. ciblée: {row['total_age_population']}"
        ).add_to(m)

    # --- GRAPHIQUE PLOTLY ---
    df_sorted = df_filtered.sort_values('H/F', ascending=True)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_sorted['LIBGEO'],
        x=df_sorted['H/F'],
        orientation='h',
        # MODIFICATION 4: Utilisation de la nouvelle fonction de couleur pour les barres
        marker=dict(
            color=[get_color_for_profile(ratio, profile) for ratio in df_sorted['H/F']],
            line=dict(width=0)
        ),
        hovertemplate='<b>%{y}</b><br>' +
                      'Ratio H/F: %{x:.1f}<br>' +
                      '<extra></extra>'
    ))

    # MODIFICATION 5: Titre du graphique dynamique
    profile_text = "un homme" if profile == "Un homme" else "une femme"
    fig.update_layout(
        title=dict(
            text=f"Analyse du ratio H/F pour {profile_text} (tranche d'âge {age_min}-{age_max} ans)",
            x=0.5,
            y=0.98
        ),
        xaxis_title="Ratio Hommes / Femmes (100 = parité)",
        yaxis_title="Villes",
        height=800,
        margin=dict(l=200, r=20, t=40, b=20),
        showlegend=False,
        plot_bgcolor='#0F1116',
        xaxis=dict(gridcolor='gray', zerolinecolor='white', zerolinewidth=1),
        yaxis=dict(showgrid=False)
    )
    fig.add_vline(x=100, line_width=2, line_dash="dash", line_color="white")

    # --- AFFICHAGE ---
    col_map, col_chart = st.columns(2)

    with col_map:
        st_folium(m, width="100%", height=700, returned_objects=[])
        
    with col_chart:
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("<div style='margin-top: -1rem; font-size: 0.8em; text-align: right;'>Source INSEE 2021</div>", unsafe_allow_html=True)
