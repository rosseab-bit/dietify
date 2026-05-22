#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import sqlite3
from typing import List, Dict, Any, Optional

# Intentar auto-ejecutar el script con el entorno virtual si no está importado experta
# 1. Monkeypatch collections para compatibilidad de experta en Python 3.10+
import collections
import collections.abc
collections.Mapping = collections.abc.Mapping
collections.MutableMapping = collections.abc.MutableMapping
collections.Sequence = collections.abc.Sequence
collections.MutableSequence = collections.abc.MutableSequence
collections.Iterable = collections.abc.Iterable
collections.MutableSet = collections.abc.MutableSet
collections.Callable = collections.abc.Callable

try:
    import experta
except ImportError:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if sys.platform == "win32":
        venv_python = os.path.join(script_dir, "venv", "Scripts", "python.exe")
    else:
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

# Importar funciones desde el módulo modularizado 'core'
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
