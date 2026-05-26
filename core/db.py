import os
import sqlite3
import json
from typing import List, Dict, Any, Optional

# Definir la ruta de la base de datos de manera que quede en la raíz del proyecto
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dietify.db")

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
    
    # El archivo seed.json está en la carpeta raíz del proyecto (un nivel arriba de core/)
    seed_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed.json")
    try:
        with open(seed_file_path, "r", encoding="utf-8") as f:
            recipes_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {seed_file_path}")
        return
    
    for r in recipes_data:
        # Verificar si la receta ya existe por su nombre
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
