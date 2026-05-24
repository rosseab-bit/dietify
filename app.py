import streamlit as st
from core.db import init_db, db_seed_inventory_from_json, db_seed_recipes_from_json
from ui.sidebar import render_sidebar
from ui.views import render_css, render_recommendation_tab, render_inventory_tab, render_catalog_tab

def main():
    # Asegurar que la DB esté inicializada al arrancar la app
    init_db()

    # Inicializar los flags en el session_state si no existen
    if "recipes_seeded" not in st.session_state:
        st.session_state["recipes_seeded"] = False
    if "inventory_seeded" not in st.session_state:
        st.session_state["inventory_seeded"] = False

    # 3. Correr las siembras SOLO si no se hicieron en esta sesión de la app
    if not st.session_state["recipes_seeded"]:
        db_seed_recipes_from_json()
        st.session_state["recipes_seeded"] = True
        
    if not st.session_state["inventory_seeded"]:
        db_seed_inventory_from_json()
        st.session_state["inventory_seeded"] = True

    # Configuración de Streamlit
    st.set_page_config(
        page_title="Dietify - Sistema Experto",
        page_icon="🥗",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Inyectar estilos
    render_css()

    st.title("🥗 Dietify — Sistema Experto Nutricional")
    st.markdown("Recomendaciones de alimentación inteligentes mediante un motor de inferencia.")

    # Renderizar panel lateral y capturar el estado
    diet_type, constraints, target, selected_meals = render_sidebar()

    # Pestañas principales
    tab1, tab2, tab3 = st.tabs(["🎯 Generar Recomendación", "📦 Mi Alacena / Inventario", "📖 Catálogo de Recetas"])

    with tab1:
        render_recommendation_tab(diet_type, constraints, target, selected_meals)
    
    with tab2:
        render_inventory_tab()
        
    with tab3:
        render_catalog_tab()

if __name__ == "__main__":
    main()