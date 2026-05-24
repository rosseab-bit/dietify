import streamlit as st
from core.db import db_get_inventory, db_update_inventory, db_delete_inventory_item, db_clear_inventory, db_get_recipes, db_create_recipe
from core.engine import run_expert_system, plan_menus
import sqlite3

def render_css():
    st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .stButton>button { background-color: #4CAF50; color: white; border-radius: 8px; border: none; padding: 10px 24px; transition: 0.3s; }
        .stButton>button:hover { background-color: #45a049; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); }
        .recipe-card { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; border-left: 5px solid #4CAF50; }
        .recipe-card-near { background-color: #1e1e1e; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; border-left: 5px solid #ff9800; }
        .meal-badge-breakfast { background-color: #ffe0b2; color: #e65100; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 0.85em; }
        .meal-badge-lunch { background-color: #c8e6c9; color: #1b5e20; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 0.85em; }
        .meal-badge-dinner { background-color: #bbdefb; color: #0d47a1; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 0.85em; }
        .meal-badge-snack { background-color: #f8bbd0; color: #c2185b; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 0.85em; }
    </style>
    """, unsafe_allow_html=True)

def render_recommendation_tab(diet_type, constraints, target, selected_meals):
    st.header("🔍 Planificador de Comidas Inteligente")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Ingredientes Disponibles")
        origen_opt = st.radio("Seleccionar origen de los alimentos:", ["Solo mi alacena guardada", "Solo ingredientes manuales ahora", "Combinar alacena + manuales"])
        
        manual_items = []
        if origen_opt in ["Solo ingredientes manuales ahora", "Combinar alacena + manuales"]:
            manual_input = st.text_area("Ingresa ingredientes manuales adicionales (separados por comas):", placeholder="ej: huevo, tomate, avena, leche")
            if manual_input: manual_items = [i.strip().lower() for i in manual_input.split(",") if i.strip()]
        
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
            st.warning("⚠️ No se han definido ingredientes.")
            
        btn_generar = st.button("🚀 Generar Menú con Sistema Experto")
        
    with col2:
        if btn_generar:
            all_recipes = db_get_recipes()
            if not all_recipes:
                st.error("No hay recetas cargadas en el catálogo.")
            else:
                with st.spinner("Procesando inferencia..."):
                    resultados = run_expert_system(diet_type=diet_type, constraints=constraints, available_ingredients=avail_names, all_recipes=all_recipes)
                    plan = plan_menus(resultados["eligible"], target, all_recipes, selected_meals=selected_meals)
                
                st.success("🎉 ¡Menú generado exitosamente!")
                
                if target == "day":
                    for meal in selected_meals:
                        rec_data = plan["day_menu"].get(meal)
                        if rec_data:
                            recipe, status, missing, reason = rec_data["recipe"], rec_data["status"], rec_data["missing_ingredients"], rec_data.get("reason", "")
                            meal_es = {"breakfast": "DESAYUNO", "lunch": "ALMUERZO", "dinner": "CENA", "snack": "MERIENDA"}.get(meal)
                            card_class = "recipe-card" if status == "exact" else "recipe-card-near"
                            status_html = '<span style="color:#4CAF50;">✓ EXACTO</span>' if status == "exact" else '<span style="color:#ff9800;">✗ CASI COMPLETO</span>'
                            
                            st.markdown(f"""
                            <div class="{card_class}">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                                    <span class="meal-badge-{meal}">{meal_es}</span> <span>Estado: {status_html}</span>
                                </div>
                                <h3>{recipe['name']}</h3>
                                <div style="background-color: #334733; padding: 10px; border-radius: 5px;"><strong>💡 Por qué:</strong> {reason}</div>
                                <p><strong>Dietas:</strong> {", ".join(recipe['diet_tags'])}</p>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    for day_plan in plan["week_menu"]:
                        st.subheader(f"📅 Día {day_plan['day_number']}")
                        cols = st.columns(max(1, len(selected_meals)))
                        for idx, meal in enumerate(selected_meals):
                            rec_data = day_plan["menu"].get(meal)
                            with cols[idx]:
                                if rec_data:
                                    recipe, status, reason = rec_data["recipe"], rec_data["status"], rec_data.get("reason", "")
                                    meal_es = {"breakfast": "Desayuno", "lunch": "Almuerzo", "dinner": "Cena", "snack": "Merienda"}.get(meal)
                                    st.markdown(f"**{meal_es}**\n\n**{recipe['name']}**")
                                    st.caption(f"{'🟢 Exacto' if status == 'exact' else '🟡 Casi completo'} | 💡 {reason}")
                        st.markdown("---")

                st.write("") 
                with st.expander("🩺 Auditoría de Inferencia del Sistema Experto"):
                    if not resultados["excluded"]:
                        st.info("No hubo descartes médicos.")
                    else:
                        for ex in resultados["excluded"]:
                            st.markdown(f"""
                            <div style="border-left: 4px solid #ff4b4b; padding-left: 10px; margin-bottom: 10px;">
                                <strong style="color: #ff4b4b;">{ex['name']}</strong><br>
                                <span style="color: #d88714;"><em>Motivo:</em></span> {ex['reason']}
                            </div>
                            """, unsafe_allow_html=True)

def render_inventory_tab():
    st.header("📦 Control de Despensa e Inventario")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Agregar Alimento")
        with st.form("inventory_form", clear_on_submit=True):
            name = st.text_input("Nombre:").strip().lower()
            qty = st.number_input("Cantidad:", min_value=0.0, step=0.1, value=1.0)
            unit = st.text_input("Unidad:").strip().lower()
            if st.form_submit_button("💾 Guardar"):
                if name and unit:
                    db_update_inventory(name, qty, unit)
                    st.success("Guardado")
                    st.rerun()
        if st.button("🚨 Vaciar alacena"):
            db_clear_inventory()
            st.rerun()

    with col2:
        st.subheader("Ingredientes Guardados")
        inventory = db_get_inventory()
        if inventory:
            for item in inventory:
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"🍏 **{item['name'].capitalize()}**")
                c2.write(f"{item['quantity']} {item['unit']}")
                if c3.button("Eliminar", key=f"del_{item['name']}"):
                    db_delete_inventory_item(item['name'])
                    st.rerun()

def render_catalog_tab():
    st.header("📖 Catálogo de Recetas")
    col1, col2 = st.columns([2, 1])
    with col1:
        recipes = db_get_recipes()
        for r in recipes:
            st.markdown(f"### {r['name']}")
            st.write(f"**Dietas:** {', '.join(r['diet_tags'])}")
            st.markdown("---")
    with col2:
        with st.form("recipe_form", clear_on_submit=True):
            r_name = st.text_input("Nombre:")
            r_inst = st.text_area("Instrucciones:")
            r_meal = st.selectbox("Comida:", ["breakfast", "lunch", "dinner", "snack"])
            r_tags = st.text_input("Etiquetas (separadas por comas):")
            r_ings = st.text_area("Ingredientes (ej. huevo,2,unidades):")
            if st.form_submit_button("➕ Registrar"):
                if r_name and r_inst and r_ings:
                    try:
                        parsed = [{"name": p[0].strip(), "quantity": float(p[1]), "unit": p[2].strip()} for p in [line.split(",") for line in r_ings.split("\n") if line.strip()]]
                        db_create_recipe(r_name, r_inst, r_meal, [t.strip() for t in r_tags.split(",")], parsed)
                        st.success("Guardado")
                        st.rerun()
                    except Exception as e:
                        st.error("Error al guardar.")