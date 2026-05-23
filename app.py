import streamlit as st
from core.db import init_db
from ui.sidebar import render_sidebar
from ui.views import render_css, render_recommendation_tab, render_inventory_tab, render_catalog_tab

def main():
    # Asegurar que la DB esté inicializada al arrancar la app
    init_db()

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