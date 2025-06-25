import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen
from branca.colormap import LinearColormap
from streamlit_folium import st_folium
import plotly.graph_objects as go
import numpy as np

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Mating App", page_icon="❤️")

# CSS pour optimiser l'espace et masquer les éléments superflus
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        .st-emotion-cache-z5fcl4 { /* Espacement des éléments dans le conteneur principal */
             padding-top: 2rem;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)


# --- 2. FONCTIONS DE CALCUL ET DE STYLE ---

@st.cache_data
def load_data(file_path):
    """Charge les données depuis le fichier CSV."""
    return pd.read_csv(file_path)

@st.cache_data
def calculer_sex_ratio(df, age_min, age_max):
    """Calcule le sex-ratio pour une tranche d'âge donnée et retourne les 300 plus grandes villes."""
    hommes_cols = [col for col in df.columns if col.startswith('X1') and age_min <= int(col[2:]) <= age_max]
    femmes_cols = [col for col in df.columns if col.startswith('X2') and age_min <= int(col[2:]) <= age_max]
    
    df['total_hommes'] = df[hommes_cols].sum(axis=1)
    df['total_femmes'] = df[femmes_cols].sum(axis=1)
    
    # Éviter la division par zéro pour les villes sans femmes dans la tranche d'âge
    df['total_femmes'] = df['total_femmes'].replace(0, 1)

    df['total_age_population'] = df['total_hommes'] + df['total_femmes']
    df['H/F'] = (df['total_hommes'] / df['total_femmes']) * 100

    df_filtered = df[df['LIBGEO'] != 'Fleury-Mérogi']
    # On retourne les 300 plus grandes villes pour la tranche d'âge sélectionnée
    df_top_300 = df_filtered.nlargest(300, 'total_age_population')
    return df_top_300

def get_dynamic_color(ratio, profile):
    """Retourne une couleur RGB personnalisée basée sur le ratio H/F et le profil utilisateur."""
    # Vert = Favorable, Rouge = Défavorable, Blanc = Parité
    # Les seuils sont fixés à 75 (très défavorable) et 125 (très favorable) ou inversement
    
    if profile == 'Un homme':
        # Favorable = ratio bas (plus de femmes)
        if ratio <= 75: return 'rgb(0, 150, 0)'    # Vert foncé
        if ratio >= 125: return 'rgb(255, 0, 0)'   # Rouge
        if ratio == 100: return 'rgb(255, 255, 255)' # Blanc
        if ratio < 100:
            # Interpolation entre vert et blanc
            factor = (ratio - 75) / 25
            return f'rgb({int(255*factor)}, 255, {int(255*factor)})'
        else: # ratio > 100
            # Interpolation entre blanc et rouge
            factor = (ratio - 100) / 25
            return f'rgb(255, {int(255*(1-factor))}, {int(255*(1-factor))})'
    else: # Pour "Une femme"
        # Favorable = ratio élevé (plus d'hommes)
        if ratio >= 125: return 'rgb(0, 150, 0)'   # Vert foncé
        if ratio <= 75: return 'rgb(255, 0, 0)'   # Rouge
        if ratio == 100: return 'rgb(255, 255, 255)' # Blanc
        if ratio > 100:
            # Interpolation entre vert et blanc
            factor = (125 - ratio) / 25
            return f'rgb({int(255*factor)}, 255, {int(255*factor)})'
        else: # ratio < 100
            # Interpolation entre blanc et rouge
            factor = (100 - ratio) / 25
            return f'rgb(255, {int(255*(1-factor))}, {int(255*(1-factor))})'


# --- 3. BARRE LATERALE DE CONTROLES (SIDEBAR) ---
df_source = load_data('df.csv')

with st.sidebar:
    st.image("https://em-content.zobj.net/source/apple/391/red-heart_2764-fe0f.png", width=60)
    st.title("Mating App")
    st.markdown("Trouvez votre prochaine destination.")
    
    st.header("1. Définissez votre profil", divider='rainbow')
    user_profile = st.radio(
        "Vous êtes :",
        ("Un homme", "Une femme"),
        horizontal=True
    )
    age_min, age_max = st.slider(
        "Vous recherchez une personne âgée de :",
        0, 100, (20, 30)
    )

    # Calcul des données basé sur les filtres d'âge
    df_top_300 = calculer_sex_ratio(df_source.copy(), age_min, age_max)
    
    st.header("2. Filtrez les villes (optionnel)", divider='rainbow')
    all_cities = df_top_300['LIBGEO'].sort_values().unique()
    selected_cities = st.multiselect(
        "Choisissez une ou plusieurs villes à comparer :",
        options=all_cities,
        placeholder="Laissez vide pour voir le top 300"
    )

# --- 4. LOGIQUE D'AFFICHAGE ---

# Filtrer le dataframe pour l'affichage final
if selected_cities:
    df_display = df_top_300[df_top_300['LIBGEO'].isin(selected_cities)]
else:
    df_display = df_top_300

st.subheader(f"Analyse pour un(e) {user_profile.lower()} cherchant entre {age_min} et {age_max} ans")

# Gérer le cas où le dataframe est vide après filtrage
if df_display.empty:
    st.warning("Aucune ville ne correspond à votre sélection. Essayez de modifier vos filtres.")
else:
    pop_min = df_display['total_age_population'].min()
    pop_max = df_display['total_age_population'].max()
    
    # --- 5. CRÉATION DES VISUALISATIONS ---
    col1, col2 = st.columns(2)

    with col1:
        # Création de la carte Folium
        m = folium.Map(location=[46.603354, 1.888334], zoom_start=6, control_scale=True, tiles="cartodbdark_matter")
        Fullscreen().add_to(m)

        # Création de la colormap dynamique
        if user_profile == 'Un homme':
            colors = ['green', 'white', 'red']
            caption = 'Ratio H/F (Vert: + de femmes, Rouge: + d\'hommes)'
        else:
            colors = ['red', 'white', 'green']
            caption = 'Ratio H/F (Vert: + d\'hommes, Rouge: + de femmes)'
        
        colormap = LinearColormap(colors=colors, index=[75, 100, 125], vmin=75, vmax=125, caption=caption)
        colormap.add_to(m)

        # Ajout des cercles sur la carte
        for idx, row in df_display.iterrows():
            radius = 5 + (np.log(row['total_age_population'] + 1) - np.log(pop_min + 1)) / (np.log(pop_max + 1) - np.log(pop_min + 1)) * 25
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=radius,
                color=colormap(row['H/F']),
                fill=True,
                fill_color=colormap(row['H/F']),
                fill_opacity=0.7,
                popup=f"<strong>{row['LIBGEO']}</strong><br>Ratio H/F: {row['H/F']:.2f}<br>Population ({age_min}-{age_max} ans): {row['total_age_population']}"
            ).add_to(m)
        
        st_folium(m, width="100%", height=700, returned_objects=[])

    with col2:
        # Création du barplot horizontal Plotly
        df_sorted = df_display.sort_values('H/F', ascending=True)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_sorted['LIBGEO'],
            x=df_sorted['H/F'],
            orientation='h',
            marker=dict(
                color=[get_dynamic_color(ratio, user_profile) for ratio in df_sorted['H/F']],
                line=dict(width=0)
            ),
            hovertemplate='<b>%{y}</b><br>' +
                          'Ratio H/F: %{x:.1f}<extra></extra>'
        ))
        
        # Définition du titre du graphique
        perspective_text = "plus de femmes (favorable)" if user_profile == "Un homme" else "plus d'hommes (favorable)"
        fig.update_layout(
            title=dict(
                text=f"Classement des villes par ratio H/F<br><sup>À gauche : {perspective_text}</sup>",
                x=0.5,
                y=0.98
            ),
            xaxis_title="Ratio Hommes/Femmes (pour 100 femmes)",
            yaxis_title="",
            height=700,
            margin=dict(l=150, r=20, t=60, b=20),
            showlegend=False,
            plot_bgcolor='#0E1117',
            paper_bgcolor='#0E1117',
            font_color='white',
            yaxis=dict(
                automargin=True,
                tickfont=dict(size=10)
            ),
            xaxis=dict(gridcolor='rgba(255, 255, 255, 0.2)')
        )

        fig.add_vline(x=100, line_width=2, line_dash="dash", line_color="white")
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("<div style='margin-top: -1rem; font-size: 0.8em; text-align: right;'>Source: INSEE Recensement 2021</div>", unsafe_allow_html=True)
