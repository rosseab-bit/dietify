#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 1. Monkeypatch collections for experta compatibility in Python 3.10+
import collections
import collections.abc
collections.Mapping = collections.abc.Mapping # type: ignore
collections.MutableMapping = collections.abc.MutableMapping # type: ignore
collections.Sequence = collections.abc.Sequence # type: ignore
collections.MutableSequence = collections.abc.MutableSequence # type: ignore
collections.Iterable = collections.abc.Iterable # type: ignore
collections.MutableSet = collections.abc.MutableSet # type: ignore
collections.Callable = collections.abc.Callable # type: ignore

# Auto-re-execute using the virtual environment python if experta is not found
try:
    import experta
except ImportError:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(script_dir, "venv", "bin", "python")
    if os.path.exists(venv_python) and sys.executable != venv_python:
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print("Error: No se pudo encontrar el módulo 'experta'.")
        print("Asegúrate de haber creado el entorno virtual e instalado las dependencias:")
        print("  python3 -m venv venv")
        print("  source venv/bin/activate")
        print("  pip install -r requirements.txt")
        sys.exit(1)

import sqlite3
import random
import json
from typing import List, Dict, Any, Optional
from experta import KnowledgeEngine, Rule, Fact, MATCH, AS

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dietify.db")

# ==========================================
# 2. BASE DE DATOS Y PERSISTENCIA (SQLite3)
# ==========================================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabla de inventario
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        name TEXT PRIMARY KEY,
        quantity REAL DEFAULT 0,
        unit TEXT DEFAULT ''
    );
    """)
    
    # Tabla de recetas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        instructions TEXT NOT NULL,
        meal_type TEXT NOT NULL, -- breakfast, lunch, dinner, snack
        diet_tags TEXT NOT NULL  -- comma-separated tags
    );
    """)
    
    # Tabla de ingredientes por receta
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipe_ingredients (
        recipe_id INTEGER NOT NULL,
        ingredient_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT NOT NULL,
        PRIMARY KEY (recipe_id, ingredient_name),
        FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE
    );
    """)
    
    conn.commit()
    seed_recipes(conn)
    conn.close()

def seed_recipes(conn):
    cursor = conn.cursor()
    
    seed_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed.json")
    try:
        with open(seed_file_path, "r", encoding="utf-8") as f:
            recipes_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {seed_file_path}")
        return
    
    for r in recipes_data:
        cursor.execute("SELECT id FROM recipes WHERE name = ?", (r["name"],))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute(
                "INSERT INTO recipes (name, instructions, meal_type, diet_tags) VALUES (?, ?, ?, ?)",
                (r["name"], r["instructions"], r["meal_type"], r["diet_tags"])
            )
            recipe_id = cursor.lastrowid
            for ing_name, qty, unit in r["ingredients"]:
                cursor.execute(
                    "INSERT INTO recipe_ingredients (recipe_id, ingredient_name, quantity, unit) VALUES (?, ?, ?, ?)",
                    (recipe_id, ing_name.lower().strip(), qty, unit)
                )
            
    conn.commit()

# --- CRUD HELPERS FOR CLI ---

def db_get_inventory() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, quantity, unit FROM inventory ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def db_update_inventory(name: str, quantity: float, unit: str):
    conn = get_connection()
    cursor = conn.cursor()
    name_lower = name.strip().lower()
    
    cursor.execute("SELECT name FROM inventory WHERE name = ?", (name_lower,))
    if cursor.fetchone():
        cursor.execute("UPDATE inventory SET quantity = ?, unit = ? WHERE name = ?", (quantity, unit, name_lower))
    else:
        cursor.execute("INSERT INTO inventory (name, quantity, unit) VALUES (?, ?, ?)", (name_lower, quantity, unit))
    conn.commit()
    conn.close()

def db_delete_inventory_item(name: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    name_lower = name.strip().lower()
    cursor.execute("SELECT name FROM inventory WHERE name = ?", (name_lower,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    cursor.execute("DELETE FROM inventory WHERE name = ?", (name_lower,))
    conn.commit()
    conn.close()
    return True

def db_clear_inventory():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory")
    conn.commit()
    conn.close()

def db_get_recipes() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, instructions, meal_type, diet_tags FROM recipes ORDER BY name ASC")
    recipe_rows = cursor.fetchall()
    
    recipes = []
    for r_row in recipe_rows:
        recipe_id = r_row["id"]
        cursor.execute("SELECT ingredient_name, quantity, unit FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
        ing_rows = cursor.fetchall()
        ingredients = [dict(ing) for ing in ing_rows]
        tags = [t.strip() for t in r_row["diet_tags"].split(",") if t.strip()]
        
        recipes.append({
            "id": r_row["id"],
            "name": r_row["name"],
            "instructions": r_row["instructions"],
            "meal_type": r_row["meal_type"],
            "diet_tags": tags,
            "ingredients": ingredients
        })
    conn.close()
    return recipes

def db_create_recipe(name: str, instructions: str, meal_type: str, diet_tags: List[str], ingredients: List[Dict[str, Any]]):
    conn = get_connection()
    cursor = conn.cursor()
    tags_str = ",".join([t.strip().lower() for t in diet_tags if t.strip()])
    
    cursor.execute(
        "INSERT INTO recipes (name, instructions, meal_type, diet_tags) VALUES (?, ?, ?, ?)",
        (name, instructions, meal_type.lower().strip(), tags_str)
    )
    recipe_id = cursor.lastrowid
    
    for ing in ingredients:
        cursor.execute(
            "INSERT INTO recipe_ingredients (recipe_id, ingredient_name, quantity, unit) VALUES (?, ?, ?, ?)",
            (recipe_id, ing["name"].strip().lower(), ing["quantity"], ing["unit"].strip())
        )
    conn.commit()
    conn.close()

# ==========================================
# 3. MOTOR DEL SISTEMA EXPERTO (Experta)
# ==========================================

class RecipeFact(Fact):
    # fields: id, name, meal_type, ingredients (frozenset), tags (frozenset)
    pass

class DietProfile(Fact):
    # fields: diet_type, target, constraints (frozenset)
    pass

class AvailableSet(Fact):
    # fields: names (frozenset)
    pass

class EligibleRecipe(Fact):
    # fields: id, name, meal_type, status ("exact" or "near"), missing_ingredients (frozenset)
    pass

class DietRecommenderEngine(KnowledgeEngine):
    
    # A. Dieta Deportes
    @Rule(
        DietProfile(diet_type="sports"),
        AvailableSet(names=MATCH.avail),
        RecipeFact(id=MATCH.id, name=MATCH.name, meal_type=MATCH.mtype, ingredients=MATCH.reqs, tags=MATCH.tags)
    )
    def match_sports_recipe(self, id, name, mtype, reqs, tags, avail):
        if "sports" in tags or "high-protein" in tags or "high-carb" in tags:
            missing = reqs - avail
            if len(missing) == 0:
                self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="exact", missing_ingredients=frozenset()))
            elif len(missing) <= 2:
                self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="near", missing_ingredients=frozenset(missing)))

    # B. Dieta Control Peso
    @Rule(
        DietProfile(diet_type="weight"),
        AvailableSet(names=MATCH.avail),
        RecipeFact(id=MATCH.id, name=MATCH.name, meal_type=MATCH.mtype, ingredients=MATCH.reqs, tags=MATCH.tags)
    )
    def match_weight_recipe(self, id, name, mtype, reqs, tags, avail):
        if "weight" in tags or "low-calorie" in tags or "low-carb" in tags or "high-fiber" in tags:
            missing = reqs - avail
            if len(missing) == 0:
                self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="exact", missing_ingredients=frozenset()))
            elif len(missing) <= 2:
                self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="near", missing_ingredients=frozenset(missing)))

    # C. Dieta Médica
    @Rule(
        DietProfile(diet_type="medical", constraints=MATCH.constraints),
        AvailableSet(names=MATCH.avail),
        RecipeFact(id=MATCH.id, name=MATCH.name, meal_type=MATCH.mtype, ingredients=MATCH.reqs, tags=MATCH.tags)
    )
    def match_medical_recipe(self, id, name, mtype, reqs, tags, avail, constraints):
        is_compatible = "medical" in tags or any(c in tags for c in constraints)
        excluded = False
        
        # Diabetes: no azúcar ni miel
        if any(c in constraints for c in ["diabetic", "diabetic-friendly", "diabetes", "low-sugar"]):
            if any(term in reqs for term in ["miel", "azúcar", "azucar"]):
                excluded = True
                
        # Hipertensión: debe ser bajo en sodio
        if any(c in constraints for c in ["hypertensive", "low-sodium", "hipertension"]):
            if "low-sodium" not in tags and "easy-digest" not in tags:
                excluded = True
                
        # Bajo en grasas (low-fat)
        if "low-fat" in constraints or "bajo en grasa" in constraints:
            if any(term in reqs for term in ["mantequilla", "aceite", "aceite de oliva"]):
                if "low-fat" not in tags:
                    excluded = True

        if is_compatible and not excluded:
            missing = reqs - avail
            if len(missing) == 0:
                self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="exact", missing_ingredients=frozenset()))
            elif len(missing) <= 2:
                self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="near", missing_ingredients=frozenset(missing)))

    # D. Dieta Propia / General
    @Rule(
        DietProfile(diet_type="own"),
        AvailableSet(names=MATCH.avail),
        RecipeFact(id=MATCH.id, name=MATCH.name, meal_type=MATCH.mtype, ingredients=MATCH.reqs, tags=MATCH.tags)
    )
    def match_own_recipe(self, id, name, mtype, reqs, tags, avail):
        missing = reqs - avail
        if len(missing) == 0:
            self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="exact", missing_ingredients=frozenset()))
        elif len(missing) <= 2:
            self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="near", missing_ingredients=frozenset(missing)))

# ==========================================
# 4. LÓGICA DE PLANIFICACIÓN DE MENÚS
# ==========================================

def run_expert_system(diet_type: str, constraints: List[str], available_ingredients: List[str], all_recipes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    engine = DietRecommenderEngine()
    engine.reset()
    
    avail_set = frozenset([i.lower().strip() for i in available_ingredients])
    constraints_set = frozenset([c.lower().strip() for c in constraints])
    
    engine.declare(DietProfile(diet_type=diet_type.lower().strip(), target="day", constraints=constraints_set))
    engine.declare(AvailableSet(names=avail_set))
    
    for r in all_recipes:
        req_ingredients = frozenset([ing["ingredient_name"].lower().strip() for ing in r["ingredients"]])
        tags_set = frozenset([t.lower().strip() for t in r["diet_tags"]])
        engine.declare(RecipeFact(
            id=r["id"],
            name=r["name"],
            meal_type=r["meal_type"].lower(),
            ingredients=req_ingredients,
            tags=tags_set
        ))
        
    engine.run()
    
    eligible = []
    for fact_id, fact in engine.facts.items():
        if isinstance(fact, EligibleRecipe):
            original = next((r for r in all_recipes if r["id"] == fact["id"]), None)
            if original:
                eligible.append({
                    "recipe": original,
                    "status": fact["status"],
                    "missing_ingredients": list(fact["missing_ingredients"])
                })
                
    eligible.sort(key=lambda x: (0 if x["status"] == "exact" else len(x["missing_ingredients"])))
    return eligible

def plan_menus(eligible_recipes: List[Dict[str, Any]], target: str, all_recipes: List[Dict[str, Any]]) -> Dict[str, Any]:
    breakfasts = [r for r in eligible_recipes if r["recipe"]["meal_type"] == "breakfast"]
    lunches = [r for r in eligible_recipes if r["recipe"]["meal_type"] in ["lunch", "dinner"]]
    dinners = [r for r in eligible_recipes if r["recipe"]["meal_type"] in ["lunch", "dinner"]]
    
    def get_fallbacks(meal_type: str) -> List[Dict[str, Any]]:
        fallbacks = []
        for r in all_recipes:
            if r["meal_type"] == meal_type or (meal_type in ["lunch", "dinner"] and r["meal_type"] in ["lunch", "dinner"]):
                if not any(el["recipe"]["id"] == r["id"] for el in eligible_recipes):
                    fallbacks.append({
                        "recipe": r,
                        "status": "near",
                        "missing_ingredients": [ing["ingredient_name"] for ing in r["ingredients"]]
                    })
        return fallbacks
        
    if not breakfasts:
        breakfasts = get_fallbacks("breakfast")
    if not lunches:
        lunches = get_fallbacks("lunch")
    if not dinners:
        dinners = get_fallbacks("dinner")

    def pick_meal(options: List[Dict[str, Any]], used_ids: List[int]) -> Dict[str, Any]:
        if not options:
            return None
        unused = [o for o in options if o["recipe"]["id"] not in used_ids]
        if unused:
            chosen = unused[0]
        else:
            slice_size = min(3, len(options))
            chosen = random.choice(options[:slice_size])
        used_ids.append(chosen["recipe"]["id"])
        return chosen

    if target == "day":
        used_ids = []
        b_meal = pick_meal(breakfasts, used_ids)
        l_meal = pick_meal(lunches, used_ids)
        d_meal = pick_meal(dinners, used_ids)
        return {"day_menu": {"breakfast": b_meal, "lunch": l_meal, "dinner": d_meal}, "week_menu": None}
    else:
        week_menu = []
        used_ids = []
        for day in range(1, 8):
            if len(used_ids) > 6:
                used_ids = used_ids[-3:]
            b_meal = pick_meal(breakfasts, used_ids)
            l_meal = pick_meal(lunches, used_ids)
            d_meal = pick_meal(dinners, used_ids)
            week_menu.append({"day_number": day, "menu": {"breakfast": b_meal, "lunch": l_meal, "dinner": d_meal}})
        return {"day_menu": None, "week_menu": week_menu}

# ==========================================
# 5. INTERFAZ DE CONSOLA INTERACTIVA (CLI)
# ==========================================

def print_banner(title: str):
    print("\n" + "="*60)
    print(f" {title.center(58)} ")
    print("="*60)

def cli_recomendar_menu():
    print_banner("RECOMENDAR MENÚS CON SISTEMA EXPERTO")
    
    # 1. Tipo de dieta
    print("Selecciona tu tipo de dieta:")
    print("1) Deportes (alto valor proteico/carbohidratos)")
    print("2) Control de Peso (bajo en calorías/carbohidratos)")
    print("3) Médica (dietas de salud / exclusión de ingredientes)")
    print("4) Propia / General (sin restricciones específicas)")
    
    dieta_opt = input("Opción (1-4): ").strip()
    if dieta_opt == "1":
        diet_type = "sports"
    elif dieta_opt == "2":
        diet_type = "weight"
    elif dieta_opt == "3":
        diet_type = "medical"
    else:
        diet_type = "own"
        
    # 2. Restricciones médicas si aplica
    constraints = []
    if diet_type == "medical":
        print("\nSelecciona o ingresa las restricciones médicas (separadas por comas):")
        print("Ejemplos comunes: diabetic-friendly (diabetes), low-sodium (hipertensión), low-fat")
        c_input = input("Restricciones: ").strip().lower()
        constraints = [c.strip() for c in c_input.split(",") if c.strip()]
        if not constraints:
            print("(!) No ingresaste restricciones específicas. Se usará el filtro médico general.")
            constraints = ["medical"]

    # 3. Período
    print("\nSelecciona el período de recomendación:")
    print("1) Menú para un día")
    print("2) Menú para una semana (7 días)")
    periodo_opt = input("Opción (1-2): ").strip()
    target = "week" if periodo_opt == "2" else "day"
    
    # 4. Origen de alimentos
    print("\n¿Qué ingredientes deseas usar?")
    print("1) Usar ingredientes guardados en la alacena / heladera")
    print("2) Ingresar ingredientes manualmente ahora mismo")
    print("3) Combinar ambos (guardados + manuales)")
    origen_opt = input("Opción (1-3): ").strip()
    
    avail_names = []
    
    # Cargar ingredientes guardados
    if origen_opt in ["1", "3"]:
        inventory = db_get_inventory()
        avail_names.extend([i["name"] for i in inventory])
        print(f"-> Cargados {len(inventory)} ingredientes de tu base de datos.")
        
    # Cargar ingredientes manuales
    if origen_opt in ["2", "3"]:
        print("\nIntroduce los ingredientes adicionales disponibles separados por comas:")
        print("Ej: huevo, tomate, leche, arroz, avena")
        manual_input = input("Ingredientes: ").strip().lower()
        manual_items = [i.strip() for i in manual_input.split(",") if i.strip()]
        avail_names.extend(manual_items)
        
    # Quitar duplicados y normalizar
    avail_names = list(set([i.lower().strip() for i in avail_names if i.strip()]))
    
    if not avail_names:
        print("\n[!] ADVERTENCIA: No se definieron ingredientes. Se sugerirán platos mostrando todos sus ingredientes como faltantes.")
        
    # 5. Ejecutar Recomendación
    all_recipes = db_get_recipes()
    if not all_recipes:
        print("\n[!] ERROR: No hay recetas en la base de datos para recomendar. Agrega algunas recetas primero.")
        return
        
    eligible = run_expert_system(
        diet_type=diet_type,
        constraints=constraints,
        available_ingredients=avail_names,
        all_recipes=all_recipes
    )
    
    plan = plan_menus(eligible, target, all_recipes)
    
    # 6. Mostrar Resultados
    print_banner(f"RECOMENDACIÓN GENERADA ({diet_type.upper()} - {target.upper()})")
    print(f"Ingredientes considerados en tu cocina: {', '.join(avail_names) if avail_names else 'Ninguno'}\n")
    
    if target == "day":
        menu = plan["day_menu"]
        for meal in ["breakfast", "lunch", "dinner"]:
            rec_data = menu.get(meal)
            print_meal_recommendation(meal, rec_data)
    else:
        for day_plan in plan["week_menu"]:
            print(f"\n--- DÍA {day_plan['day_number']} " + "-"*48)
            for meal in ["breakfast", "lunch", "dinner"]:
                rec_data = day_plan["menu"].get(meal)
                print_meal_recommendation(meal, rec_data, compact=True)
                
    input("\nPresiona Enter para volver al menú principal...")

def print_meal_recommendation(meal_name: str, rec_data: Optional[Dict[str, Any]], compact: bool = False):
    meal_es = {"breakfast": "DESAYUNO", "lunch": "ALMUERZO", "dinner": "CENA"}.get(meal_name, meal_name.upper())
    
    if not rec_data:
        print(f" * {meal_es}: No se encontró ninguna receta compatible.")
        return
        
    recipe = rec_data["recipe"]
    status = rec_data["status"]
    missing = rec_data["missing_ingredients"]
    
    status_str = "✓ EXACTO" if status == "exact" else f"✗ CASI COMPLETO (Falta comprar: {', '.join(missing)})"
    
    if compact:
        print(f" * {meal_es}: {recipe['name']} [{status_str}]")
    else:
        print(f"=== {meal_es} ===")
        print(f"Receta: {recipe['name']}")
        print(f"Estado de cocina: {status_str}")
        print("Ingredientes requeridos:")
        for ing in recipe["ingredients"]:
            print(f"  - {ing['ingredient_name'].capitalize()}: {ing['quantity']} {ing['unit']}")
        print("Instrucciones de preparación:")
        print(f"  {recipe['instructions']}")
        print("-" * 60)

def cli_gestionar_inventario():
    while True:
        print_banner("GESTIONAR ALACENA / HELADERA (INVENTARIO)")
        inventory = db_get_inventory()
        if not inventory:
            print("Tu alacena y heladera están vacías.")
        else:
            print("Alimentos disponibles actualmente:")
            print(f"{'Ingrediente':<25} | {'Cantidad':<10} | {'Unidad':<10}")
            print("-" * 51)
            for item in inventory:
                print(f"{item['name'].capitalize():<25} | {item['quantity']:<10.2f} | {item['unit']:<10}")
                
        print("\nOpciones de inventario:")
        print("1) Agregar / Modificar ingrediente")
        print("2) Eliminar ingrediente")
        print("3) Vaciar inventario por completo")
        print("4) Volver al menú principal")
        
        opt = input("Opción (1-4): ").strip()
        if opt == "1":
            name = input("Nombre del ingrediente (ej. huevo): ").strip().lower()
            if not name:
                continue
            try:
                qty = float(input("Cantidad (ej. 5): ").strip())
            except ValueError:
                print("(!) Cantidad inválida, se usará 0.")
                qty = 0.0
            unit = input("Unidad de medida (ej. unidades, g, ml): ").strip()
            db_update_inventory(name, qty, unit)
            print(f"-> Guardado exitosamente: {name.capitalize()} ({qty} {unit})")
        elif opt == "2":
            name = input("Nombre del ingrediente a eliminar: ").strip().lower()
            if db_delete_inventory_item(name):
                print(f"-> Ingrediente '{name}' eliminado de tu inventario.")
            else:
                print(f"(!) El ingrediente '{name}' no existe en el inventario.")
        elif opt == "3":
            confirm = input("¿Estás seguro de que deseas vaciar tu alacena? (s/n): ").strip().lower()
            if confirm == "s":
                db_clear_inventory()
                print("-> Inventario vaciado por completo.")
        else:
            break

def cli_ver_recetas():
    print_banner("CATÁLOGO DE RECETAS EN EL SISTEMA")
    recipes = db_get_recipes()
    if not recipes:
        print("No hay recetas registradas en el sistema.")
    else:
        for r in recipes:
            print(f"\nID: {r['id']} - {r['name'].upper()} ({r['meal_type'].capitalize()})")
            print(f"Dietas compatibles: {', '.join(r['diet_tags'])}")
            print("Ingredientes necesarios:")
            for ing in r["ingredients"]:
                print(f"  - {ing['ingredient_name'].capitalize()}: {ing['quantity']} {ing['unit']}")
            print("Instrucciones básicas:")
            print(f"  {r['instructions']}")
            print("-" * 60)
            
    input("\nPresiona Enter para volver...")

def cli_crear_receta():
    print_banner("REGISTRAR NUEVA RECETA")
    name = input("Nombre de la receta (ej. Arroz con Huevo): ").strip()
    if not name:
        return
    instructions = input("Instrucciones paso a paso: ").strip()
    if not instructions:
        return
        
    print("\nTipo de comida:")
    print("1) Desayuno (breakfast)")
    print("2) Almuerzo/Cena (lunch)")
    print("3) Merienda/Snack (snack)")
    m_opt = input("Opción (1-3): ").strip()
    meal_type = "breakfast" if m_opt == "1" else "lunch" if m_opt == "2" else "snack"
    
    tags_input = input("\nEtiquetas de dieta (separadas por comas, ej: sports, high-protein, medical, weight): ").strip()
    diet_tags = [t.strip().lower() for t in tags_input.split(",") if t.strip()]
    
    ingredients = []
    print("\nIngrese los ingredientes de la receta (deje el nombre vacío o escriba 'fin' para terminar):")
    while True:
        ing_name = input("  Nombre del ingrediente: ").strip().lower()
        if not ing_name or ing_name == "fin":
            break
        try:
            qty = float(input(f"  Cantidad para {ing_name}: ").strip())
        except ValueError:
            print("  (!) Cantidad inválida, se registrará como 0.")
            qty = 0.0
        unit = input(f"  Unidad para {ing_name} (ej. g, ml, unidades): ").strip()
        ingredients.append({"name": ing_name, "quantity": qty, "unit": unit})
        print()
        
    if not ingredients:
        print("(!) Una receta debe tener al menos un ingrediente. Cancelando registro.")
        return
        
    try:
        db_create_recipe(name, instructions, meal_type, diet_tags, ingredients)
        print(f"\n-> ¡Receta '{name}' guardada exitosamente en la base de datos!")
    except sqlite3.IntegrityError:
        print("\n(!) Ya existe una receta con ese nombre en el sistema.")
    except Exception as e:
        print(f"\n(!) Error al guardar la receta: {e}")
        
    input("\nPresiona Enter para volver...")

def main():
    init_db()
    while True:
        print_banner("DIETIFY - SISTEMA EXPERTO CLI")
        print("1) Recomendar menú para el día o la semana")
        print("2) Gestionar alimentos en la alacena / heladera")
        print("3) Ver catálogo de recetas en el sistema")
        print("4) Registrar una nueva receta en el catálogo")
        print("5) Salir del programa")
        print("="*60)
        
        opt = input("Selecciona una opción (1-5): ").strip()
        if opt == "1":
            cli_recomendar_menu()
        elif opt == "2":
            cli_gestionar_inventario()
        elif opt == "3":
            cli_ver_recetas()
        elif opt == "4":
            cli_crear_receta()
        elif opt == "5":
            print("\n¡Gracias por usar Dietify! ¡Hasta luego!\n")
            break
        else:
            print("(!) Opción no válida. Intenta de nuevo.")

if __name__ == "__main__":
    main()
