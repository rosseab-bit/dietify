import os
import sqlite3
import json
from typing import List, Dict, Any

# Definir la ruta de la base de datos en la raíz del proyecto[cite: 16]
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dietify.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        name TEXT PRIMARY KEY,
        quantity REAL DEFAULT 0,
        unit TEXT DEFAULT ''
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        instructions TEXT NOT NULL,
        meal_type TEXT NOT NULL,
        diet_tags TEXT NOT NULL
    );
    """)
    
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
    conn.close()

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

def db_seed_inventory_from_json():
    conn = get_connection()
    cursor = conn.cursor()
    # Comprobamos si el inventario ya tiene elementos
    cursor.execute("SELECT COUNT(*) FROM inventory")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return  # Si ya hay ingredientes, no hacemos nada para no pisar al usuario

    # Calcular la ruta al archivo en la raíz del proyecto
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "ingredient_seed.json")
        
    if not os.path.exists(json_path):
         print(f"Advertencia: No se encontró el archivo de ingredientes en {json_path}")
         conn.close()
         return

        # Leer e insertar los datos
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            ingredients = json.load(f)
                
        for ing in ingredients:
            name_lower = ing["name"].strip().lower()
            cursor.execute(
                "INSERT INTO inventory (name, quantity, unit) VALUES (?, ?, ?)",
                (name_lower, ing["quantity"], ing["unit"].strip())
            )
        conn.commit()
    except Exception as e:
        print(f"Error al sembrar el inventario: {e}")
    finally:
        conn.close() 
        
def db_seed_recipes_from_json():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Comprobamos si ya existen recetas en la base de datos
    cursor.execute("SELECT COUNT(*) FROM recipes")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return  # Si ya hay recetas, salimos para no duplicar datos

    # Calcular la ruta al archivo seed.json en la raíz del proyecto
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "seed.json")
    
    if not os.path.exists(json_path):
        print(f"Advertencia: No se encontró el archivo de recetas en {json_path}")
        conn.close()
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Controlamos si viene como lista directa o dentro de una clave "recipes"
        if isinstance(data, dict):
            recipes_list = data.get("recipes", [])
        elif isinstance(data, list):
            recipes_list = data
        else:
            recipes_list = []
            
        # Insertamos cada receta usando la función del sistema
        for r in recipes_list:
            db_create_recipe(
                name=r["name"],
                instructions=r["instructions"],
                meal_type=r["meal_type"],
                diet_tags=r["diet_tags"] if isinstance(r["diet_tags"], list) else [t.strip() for t in r["diet_tags"].split(",") if t.strip()],
                ingredients=[{"name": ing[0], "quantity": ing[1], "unit": ing[2]} for ing in r["ingredients"]]
            )
    except Exception as e:
        print(f"Error al sembrar las recetas: {e}")
    finally:
        conn.close()