import streamlit as st
import os
import sys

# Parchear collections para compatibilidad de experta
import collections
import collections.abc
collections.Mapping = collections.abc.Mapping # type: ignore
collections.MutableMapping = collections.abc.MutableMapping # type: ignore
collections.Sequence = collections.abc.Sequence # type: ignore
collections.MutableSequence = collections.abc.MutableSequence # type: ignore
collections.Iterable = collections.abc.Iterable # type: ignore
collections.MutableSet = collections.abc.MutableSet # type: ignore
collections.Callable = collections.abc.Callable # type: ignore

from core.db import (
    init_db,
    db_get_inventory,
    db_update_inventory,
    db_delete_inventory_item,
    db_clear_inventory,
    db_get_recipes,
    db_create_recipe
)
from core.engine import run_expert_system, plan_menus

# Asegurar que la DB esté inicializada al arrancar la app
init_db()

# Configuración estética de la página de Streamlit
st.set_page_config(
    page_title="Dietify - Sistema Experto de Nutrición",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS personalizado para mejorar el diseño
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #45a049;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
    }
    .recipe-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border-left: 5px solid #4CAF50;
    }
    .recipe-card-near {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border-left: 5px solid #ff9800;
    }
    .meal-badge-breakfast {
        background-color: #ffe0b2;
        color: #e65100;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85em;
    }
    .meal-badge-lunch {
        background-color: #c8e6c9;
        color: #1b5e20;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85em;
    }
    .meal-badge-dinner {
        background-color: #bbdefb;
        color: #0d47a1;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85em;
    }
    .meal-badge-snack {
        background-color: #f8bbd0;
        color: #c2185b;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85em;
    }
</style>
""", unsafe_allow_html=True)

# Título y Encabezado Principal
st.title("🥗 Dietify — Sistema Experto Nutricional")
st.markdown("Recomendaciones de alimentación inteligentes personalizadas mediante un motor de inferencia de reglas.")

# --- BARRA LATERAL (CONFIGURACIÓN DE DIETA) ---
st.sidebar.header("⚙️ Configuración del Perfil")

diet_opt = st.sidebar.selectbox(
    "Tipo de Dieta:",
    ["Deportes (Alto valor proteico/carbohidratos)", 
     "Control de Peso (Bajo en calorías/carbohidratos)", 
     "Médica (Dietas de salud y restricciones)", 
     "Propia / General (Sin restricciones específicas)"]
)

# Mapeo interno
diet_type = "own"
if "Deportes" in diet_opt:
    diet_type = "sports"
elif "Control de Peso" in diet_opt:
    diet_type = "weight"
elif "Médica" in diet_opt:
    diet_type = "medical"

# Restricciones si es médica
constraints = []
if diet_type == "medical":
    constraints = st.sidebar.multiselect(
        "Restricciones Médicas / Condiciones:",
        ["diabetic-friendly", "low-sodium", "low-fat", "easy-digest"],
        default=["diabetic-friendly"]
    )

# Período de recomendación
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

# Pestañas principales
tab_recomendar, tab_inventario, tab_catalogo = st.tabs([
    "🎯 Generar Recomendación", 
    "📦 Mi Alacena / Inventario", 
    "📖 Catálogo de Recetas"
])

# ==========================================
# PESTAÑA 1: RECOMENDADOR
# ==========================================
with tab_recomendar:
    st.header("🔍 Planificador de Comidas Inteligente")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Ingredientes Disponibles")
        origen_opt = st.radio(
            "Seleccionar origen de los alimentos:",
            ["Solo mi alacena guardada", "Solo ingredientes manuales ahora", "Combinar alacena + manuales"]
        )
        
        manual_items = []
        if origen_opt in ["Solo ingredientes manuales ahora", "Combinar alacena + manuales"]:
            manual_input = st.text_area(
                "Ingresa ingredientes manuales adicionales (separados por comas):",
                placeholder="ej: huevo, tomate, avena, leche",
                help="Escribe los ingredientes que tienes a mano en este momento."
            )
            if manual_input:
                manual_items = [i.strip().lower() for i in manual_input.split(",") if i.strip()]
        
        # Cargar los nombres disponibles
        avail_names = []
        if origen_opt in ["Solo mi alacena guardada", "Combinar alacena + manuales"]:
            inventory = db_get_inventory()
            avail_names.extend([i["name"] for i in inventory])
            st.info(f"💾 Se considerarán {len(inventory)} ingredientes de tu inventario guardado.")
            
        avail_names.extend(manual_items)
        avail_names = list(set([i.lower().strip() for i in avail_names if i.strip()]))
        
        if avail_names:
            st.write("**Total ingredientes considerados:**")
            st.caption(", ".join(avail_names))
        else:
            st.warning("⚠️ No se han definido ingredientes. El sistema sugerirá menús marcando todos sus ingredientes como faltantes.")
            
        btn_generar = st.button("🚀 Generar Menú con Sistema Experto")
        
    with col2:
        if btn_generar:
            all_recipes = db_get_recipes()
            if not all_recipes:
                st.error("No hay recetas cargadas en el catálogo. Por favor agrégalas primero.")
            else:
                with st.spinner("El motor de reglas de Experta está analizando tu perfil nutricional y despensa..."):
                    eligible = run_expert_system(
                        diet_type=diet_type,
                        constraints=constraints if diet_type == "medical" else [],
                        available_ingredients=avail_names,
                        all_recipes=all_recipes
                    )
                    plan = plan_menus(eligible, target, all_recipes, selected_meals=selected_meals)
                
                st.success("🎉 ¡Menú generado exitosamente!")
                
                # Mostrar resultados
                if target == "day":
                    menu = plan["day_menu"]
                    for meal in selected_meals:
                        rec_data = menu.get(meal)
                        if rec_data:
                            recipe = rec_data["recipe"]
                            status = rec_data["status"]
                            missing = rec_data["missing_ingredients"]
                            
                            badge_style = meal
                            meal_es = {"breakfast": "DESAYUNO", "lunch": "ALMUERZO", "dinner": "CENA", "snack": "MERIENDA"}.get(meal)
                            
                            card_class = "recipe-card" if status == "exact" else "recipe-card-near"
                            status_html = '<span style="color:#4CAF50; font-weight:bold;">✓ EXACTO</span>' if status == "exact" else f'<span style="color:#ff9800; font-weight:bold;">✗ CASI COMPLETO</span>'
                            
                            st.markdown(f"""
                            <div class="{card_class}">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                                    <span class="meal-badge-{badge_style}">{meal_es}</span>
                                    <span>Estado: {status_html}</span>
                                </div>
                                <h3 style="margin-top:5px; margin-bottom:10px;">{recipe['name']}</h3>
                                <p><strong>Dietas:</strong> {", ".join(recipe['diet_tags'])}</p>
                                <p><strong>Instrucciones:</strong> {recipe['instructions']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Mostrar ingredientes
                            with st.expander(f"Ver ingredientes para {recipe['name']}"):
                                for ing in recipe["ingredients"]:
                                    st.write(f"- **{ing['ingredient_name'].capitalize()}**: {ing['quantity']} {ing['unit']}")
                                if status == "near" and missing:
                                    st.markdown(f"⚠️ **Falta comprar:** <span style='color:#ff9800;'>{', '.join(missing)}</span>", unsafe_allow_html=True)
                            st.markdown("<hr>", unsafe_allow_html=True)
                else:
                    # Semanal
                    for day_plan in plan["week_menu"]:
                        st.subheader(f"📅 Día {day_plan['day_number']}")
                        num_cols = max(1, len(selected_meals))
                        cols = st.columns(num_cols)
                        for idx, meal in enumerate(selected_meals):
                            rec_data = day_plan["menu"].get(meal)
                            with cols[idx]:
                                if rec_data:
                                    recipe = rec_data["recipe"]
                                    status = rec_data["status"]
                                    missing = rec_data["missing_ingredients"]
                                    
                                    meal_es = {"breakfast": "Desayuno", "lunch": "Almuerzo", "dinner": "Cena", "snack": "Merienda"}.get(meal)
                                    status_icon = "🟢" if status == "exact" else "🟡"
                                    
                                    st.markdown(f"**{meal_es}**")
                                    st.markdown(f"**{recipe['name']}**")
                                    st.caption(f"{status_icon} {'Exacto' if status == 'exact' else 'Casi completo'}")
                                    if status == "near" and missing:
                                        st.caption(f"Falta: {', '.join(missing)}")
                                    with st.expander("Ver preparación"):
                                        st.write(recipe["instructions"])
                        st.markdown("---")
        else:
            st.info("Configura las opciones en el panel izquierdo y haz clic en 'Generar Menú' para visualizar tu plan de alimentación.")

# ==========================================
# PESTAÑA 2: INVENTARIO
# ==========================================
with tab_inventario:
    st.header("📦 Control de Despensa e Inventario")
    st.markdown("Agrega los alimentos que posees en tu heladera o alacena para que el motor de reglas los considere en la preparación.")
    
    col_inv1, col_inv2 = st.columns([1, 2])
    
    with col_inv1:
        st.subheader("Agregar / Modificar Alimento")
        with st.form("inventory_form", clear_on_submit=True):
            item_name = st.text_input("Nombre del alimento:", placeholder="ej: huevo, avena, leche").strip().lower()
            item_qty = st.number_input("Cantidad:", min_value=0.0, step=0.1, value=1.0)
            item_unit = st.text_input("Unidad de medida:", placeholder="ej: unidades, g, ml, rebanadas").strip().lower()
            
            submit_inv = st.form_submit_button("💾 Guardar en Despensa")
            
            if submit_inv:
                if item_name and item_unit:
                    db_update_inventory(item_name, item_qty, item_unit)
                    st.success(f"Guardado: {item_name.capitalize()} ({item_qty} {item_unit})")
                    st.rerun()
                else:
                    st.error("Por favor completa el nombre del ingrediente y la unidad de medida.")
                    
        # Vaciar alacena
        st.markdown("---")
        st.subheader("Acciones de Peligro")
        if st.button("🚨 Vaciar alacena por completo"):
            db_clear_inventory()
            st.warning("Inventario borrado por completo.")
            st.rerun()

    with col_inv2:
        st.subheader("Ingredientes Guardados")
        inventory = db_get_inventory()
        
        if not inventory:
            st.info("Tu despensa está vacía. ¡Ingresa ingredientes para comenzar!")
        else:
            for item in inventory:
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"🍏 **{item['name'].capitalize()}**")
                c2.write(f"{item['quantity']} {item['unit']}")
                if c3.button("Eliminar", key=f"del_{item['name']}"):
                    db_delete_inventory_item(item['name'])
                    st.success(f"Removido {item['name']}")
                    st.rerun()

# ==========================================
# PESTAÑA 3: CATÁLOGO DE RECETAS
# ==========================================
with tab_catalogo:
    st.header("📖 Catálogo de Recetas")
    
    col_cat1, col_cat2 = st.columns([2, 1])
    
    with col_cat1:
        st.subheader("Lista de Recetas")
        recipes = db_get_recipes()
        
        if not recipes:
            st.info("No hay recetas en el catálogo.")
        else:
            for r in recipes:
                st.markdown(f"### {r['name']} ({r['meal_type'].capitalize()})")
                st.write(f"**Dietas compatibles:** {', '.join(r['diet_tags'])}")
                
                # Ingredientes requeridos
                ing_list = []
                for ing in r["ingredients"]:
                    ing_list.append(f"{ing['ingredient_name'].capitalize()} ({ing['quantity']} {ing['unit']})")
                st.write(f"**Ingredientes:** {', '.join(ing_list)}")
                st.write(f"**Instrucciones:** {r['instructions']}")
                st.markdown("---")
                
    with col_cat2:
        st.subheader("Registrar Nueva Receta")
        with st.form("recipe_form", clear_on_submit=True):
            r_name = st.text_input("Nombre de la receta (ej: Ensalada César):").strip()
            r_instructions = st.text_area("Instrucciones de preparación:").strip()
            r_meal_type = st.selectbox("Tipo de comida:", ["breakfast", "lunch", "dinner", "snack"])
            r_tags_input = st.text_input("Etiquetas de dieta (separadas por comas, ej: sports, low-fat):").strip()
            
            st.markdown("**Ingredientes requeridos (ej. ingrediente,cantidad,unidad):**")
            st.caption("Ingresa uno por línea. Ejemplo: huevo,2,unidades")
            r_ings_input = st.text_area("Ingredientes:", placeholder="tomate,1,unidad\nqueso,30,g")
            
            submit_recipe = st.form_submit_button("➕ Registrar Receta")
            
            if submit_recipe:
                if r_name and r_instructions and r_ings_input:
                    # Parsear ingredientes
                    parsed_ings = []
                    lines = r_ings_input.split("\n")
                    valid = True
                    for line in lines:
                        if not line.strip():
                            continue
                        parts = line.split(",")
                        if len(parts) == 3:
                            try:
                                parsed_ings.append({
                                    "name": parts[0].strip().lower(),
                                    "quantity": float(parts[1].strip()),
                                    "unit": parts[2].strip()
                                })
                            except ValueError:
                                st.error(f"Cantidad inválida en la línea: {line}")
                                valid = False
                        else:
                            st.error(f"Formato de ingrediente incorrecto en la línea: {line}")
                            valid = False
                            
                    if valid and parsed_ings:
                        r_tags = [t.strip().lower() for t in r_tags_input.split(",") if t.strip()]
                        try:
                            db_create_recipe(r_name, r_instructions, r_meal_type, r_tags, parsed_ings)
                            st.success(f"¡Receta '{r_name}' agregada con éxito!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Ya existe una receta con este nombre en el sistema.")
                else:
                    st.error("Por favor completa los campos obligatorios: Nombre, Instrucciones e Ingredientes.")
