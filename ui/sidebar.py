import streamlit as st

def render_sidebar():
    st.sidebar.header("⚙️ Configuración del Perfil")

    diet_opt = st.sidebar.selectbox(
        "Tipo de Dieta:",
        ["Deportes (Alto valor proteico/carbohidratos)", 
         "Control de Peso (Bajo en calorías/carbohidratos)", 
         "Médica (Dietas de salud y restricciones)", 
         "Propia / General (Sin restricciones específicas)"]
    )

    diet_type = "own"
    if "Deportes" in diet_opt:
        diet_type = "sports"
    elif "Control de Peso" in diet_opt:
        diet_type = "weight"
    elif "Médica" in diet_opt:
        diet_type = "medical"

    constraints = []
    if diet_type == "medical":
        constraints = st.sidebar.multiselect(
            "Restricciones Médicas / Condiciones:",
            ["diabetic-friendly", "low-sodium", "low-fat", "easy-digest"],
            default=["diabetic-friendly"]
        )

    periodo_opt = st.sidebar.radio(
        "Período de Menú:",
        ["Un Día", "Una Semana (7 Días)"]
    )
    target = "week" if "Semana" in periodo_opt else "day"

    st.sidebar.markdown("---")
    st.sidebar.subheader("🍽️ Comidas a incluir")
    include_breakfast = st.sidebar.checkbox("Desayuno", value=True)
    include_lunch = st.sidebar.checkbox("Almuerzo", value=True)
    include_snack = st.sidebar.checkbox("Merienda (Snack)", value=False)
    include_dinner = st.sidebar.checkbox("Cena", value=True)

    selected_meals = []
    if include_breakfast: selected_meals.append("breakfast")
    if include_lunch: selected_meals.append("lunch")
    if include_snack: selected_meals.append("snack")
    if include_dinner: selected_meals.append("dinner")
    
    return diet_type, constraints, target, selected_meals