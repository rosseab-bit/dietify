from core.db import init_db, db_get_inventory, db_update_inventory, db_delete_inventory_item, db_clear_inventory, db_get_recipes, db_create_recipe
from core.engine import run_expert_system, plan_menus
from typing import Dict, Any, Optional

def print_banner(title: str):
    print("\n" + "="*60)
    print(f" {title.center(58)} ")
    print("="*60)

def cli_recomendar_menu():
    print_banner("RECOMENDAR MENÚS CON SISTEMA EXPERTO")
    
    print("Selecciona tu tipo de dieta:")
    print("1) Deportes\n2) Control de Peso\n3) Médica\n4) Propia / General")
    dieta_opt = input("Opción (1-4): ").strip()
    diet_type = {"1": "sports", "2": "weight", "3": "medical"}.get(dieta_opt, "own")
        
    constraints = []
    if diet_type == "medical":
        c_input = input("Restricciones (ej. diabetic-friendly): ").strip().lower()
        constraints = [c.strip() for c in c_input.split(",") if c.strip()] or ["medical"]

    periodo_opt = input("\nPeríodo:\n1) Un día\n2) Una semana\nOpción (1-2): ").strip()
    target = "week" if periodo_opt == "2" else "day"
    
    print("\n¿Qué ingredientes deseas usar?\n1) Alacena\n2) Manual\n3) Ambos")
    origen_opt = input("Opción (1-3): ").strip()
    
    avail_names = []
    if origen_opt in ["1", "3"]:
        inventory = db_get_inventory()
        avail_names.extend([i["name"] for i in inventory])
        
    if origen_opt in ["2", "3"]:
        manual_input = input("Ingredientes adicionales (comas): ").strip().lower()
        avail_names.extend([i.strip() for i in manual_input.split(",") if i.strip()])
        
    avail_names = list(set([i.lower().strip() for i in avail_names if i.strip()]))
    
    all_recipes = db_get_recipes()
    if not all_recipes:
        print("\n[!] ERROR: No hay recetas en la base de datos.")
        return
        
    resultados = run_expert_system(diet_type, constraints, avail_names, all_recipes)
    plan = plan_menus(resultados["eligible"], target, all_recipes)
    
    print_banner(f"RECOMENDACIÓN GENERADA ({diet_type.upper()} - {target.upper()})")
    
    if target == "day":
        for meal in ["breakfast", "lunch", "dinner"]:
            print_meal_recommendation(meal, plan["day_menu"].get(meal))
    else:
        for day_plan in plan["week_menu"]:
            print(f"\n--- DÍA {day_plan['day_number']} " + "-"*48)
            for meal in ["breakfast", "lunch", "dinner"]:
                print_meal_recommendation(meal, day_plan["menu"].get(meal), compact=True)

    if resultados["excluded"]:
        print("\n" + "="*60 + "\n ❌ AUDITORÍA DE DESCARTES\n" + "="*60)
        for ex in resultados["excluded"]:
            print(f" * {ex['name']} \n   └─ Motivo: {ex['reason']}")
            
    input("\nPresiona Enter para volver al menú principal...")

def print_meal_recommendation(meal_name: str, rec_data: Optional[Dict[str, Any]], compact: bool = False):
    if not rec_data: return
    recipe, status, reason = rec_data["recipe"], rec_data["status"], rec_data.get("reason", "")
    meal_es = {"breakfast": "DESAYUNO", "lunch": "ALMUERZO", "dinner": "CENA"}.get(meal_name, meal_name.upper())
    
    if compact:
        print(f" * {meal_es}: {recipe['name']} [{'✓' if status == 'exact' else '✗'}]\n   └─ Por qué: {reason}")
    else:
        print(f"=== {meal_es} ===\nReceta: {recipe['name']}\nPor qué: {reason}\n{'-' * 60}")

def main():
    init_db()
    while True:
        print_banner("DIETIFY - SISTEMA EXPERTO CLI")
        print("1) Recomendar menú\n2) Salir")
        if input("Opción: ").strip() == "1":
            cli_recomendar_menu()
        else:
            break

if __name__ == "__main__":
    main()