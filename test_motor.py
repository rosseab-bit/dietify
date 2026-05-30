# test_motor.py
from core.engine import run_expert_system

# 2. DEFINIMOS EL PERFIL MÉDICO PARA QUE HAGA MATCH CON LA REGLA
tipo_dieta = "medical"
restricciones = ["diabetic", "hipertension"]     # Estas restricciones activan los filtros médicos
ingredientes_heladera = ["tomate", "mozzarella"]  # El usuario tiene estos dos

mock_recipes = [
    {
        "id": 1,
        "name": "Ensalada Caprese Médica",
        "meal_type": "lunch",
        "diet_tags": ["medical", "low-sodium"],    # "low-sodium" evita la exclusión por hipertensión
        "ingredients": [
            {"ingredient_name": "tomate"},
            {"ingredient_name": "mozzarella"},
            {"ingredient_name": "albahaca"}        # Falta este (será elegible parcial)
        ]
    },
    {
        "id": 2,
        "name": "Postre Dulce",
        "meal_type": "dinner",
        "diet_tags": ["diabetic"],       # Cambiado de "diabetic-friendly" a "diabetic"
        "ingredients": [
            {"ingredient_name": "frutillas"},
            {"ingredient_name": "azúcar"} 
        ]
    }
]

# 3. Ejecutamos tu sistema experto
print("--- EJECUTANDO SISTEMA EXPERTO ---")
resultado = run_expert_system(
    diet_type=tipo_dieta,
    constraints=restricciones,
    available_ingredients=ingredientes_heladera,
    all_recipes=mock_recipes
)

# 4. Mostramos los resultados formateados en la consola
import json
print(json.dumps(resultado, indent=4, ensure_ascii=False))