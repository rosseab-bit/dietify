import os
import sys
import random
from typing import List, Dict, Any, Optional

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

from experta import KnowledgeEngine, Rule, Fact, MATCH, AS

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
    # fields: id, name, meal_type, status ("exact" or "near"),
    # missing_ingredients (frozenset), reason
    pass

class ExcludedRecipe(Fact):
    # fields: id, name, meal_type, reason
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
            reason = "Compatible por su alto valor proteico/carbohidratos, ideal para tu dieta deportiva."
            if len(missing) == 0:
                self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="exact", missing_ingredients=frozenset(), reason=reason))
            elif len(missing) <= 2:
                self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="near", missing_ingredients=frozenset(missing), reason=reason))
            else:
                # EXCLUSIÓN TAREA 2: Cumple la dieta pero faltan ingredientes
                self.declare(ExcludedRecipe(id=id, name=name, reason=f"Faltan demasiados ingredientes ({len(missing)} faltantes) para esta receta deportiva."))
        else:
            # EXCLUSIÓN TAREA 2: No cumple las etiquetas
            self.declare(ExcludedRecipe(id=id, name=name, reason="No posee las etiquetas requeridas para rendimiento deportivo (sports, high-protein, high-carb)."))

    # B. Dieta Control Peso
    @Rule(
        DietProfile(diet_type="weight"),
        AvailableSet(names=MATCH.avail),
        RecipeFact(id=MATCH.id, name=MATCH.name, meal_type=MATCH.mtype, ingredients=MATCH.reqs, tags=MATCH.tags)
    )
    def match_weight_recipe(self, id, name, mtype, reqs, tags, avail):
        if "weight" in tags or "low-calorie" in tags or "low-carb" in tags or "high-fiber" in tags:
            missing = reqs - avail
            reason = "Compatible por su bajo aporte calórico/carbohidratos para el control de peso."
            if len(missing) == 0:
                self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="exact", missing_ingredients=frozenset(), reason=reason))
            elif len(missing) <= 2:
                self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="near", missing_ingredients=frozenset(missing), reason=reason))
            else:
                self.declare(ExcludedRecipe(id=id, name=name, reason=f"Faltan demasiados ingredientes ({len(missing)} faltantes) para control de peso."))
        else:
            self.declare(ExcludedRecipe(id=id, name=name, reason="No posee las etiquetas requeridas para control de peso (weight, low-calorie, low-carb, high-fiber)."))

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
                excluded, trigger = True, "miel o azúcar"
                
        # Hipertensión: debe ser bajo en sodio
        if any(c in constraints for c in ["hypertensive", "low-sodium", "hipertension"]):
            if "low-sodium" not in tags and "easy-digest" not in tags:
                excluded, trigger = True, "exceso de sodio (no adaptado)"
                
        # Bajo en grasas (low-fat)
        if "low-fat" in constraints or "bajo en grasa" in constraints:
            if any(term in reqs for term in ["mantequilla", "aceite", "aceite de oliva"]):
                if "low-fat" not in tags:
                    excluded, trigger = True, "exceso de grasas"

        # Si hay exclusión médica, se declara inmediatamente sin importar las etiquetas
        if excluded:
            self.declare(ExcludedRecipe(id=id, name=name, reason=f"Exclusión médica: Contiene o procesa '{trigger}', prohibido para tu condición."))
            return  # Cortamos la ejecución de esta regla para esta receta
        
        # Si pasó los filtros médicos, vemos si es compatible con el perfil de la receta
        is_compatible = "medical" in tags or any(c in tags for c in constraints)
        
        if is_compatible:
            missing = reqs - avail
            reason = "Aprobada: Cumple rigurosamente con tus restricciones médicas."
            if len(missing) == 0:
                self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="exact", missing_ingredients=frozenset(), reason=reason))
            elif len(missing) <= 2:
                self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="near", missing_ingredients=frozenset(missing), reason=reason))
            else:
                self.declare(ExcludedRecipe(id=id, name=name, reason=f"Médicamente apta, pero faltan demasiados ingredientes ({len(missing)} faltantes)."))
        else:
            self.declare(ExcludedRecipe(id=id, name=name, reason="No está etiquetada como apta para tu perfil de restricciones médicas especificado."))

    # D. Dieta Propia / General
    @Rule(
        DietProfile(diet_type="own"),
        AvailableSet(names=MATCH.avail),
        RecipeFact(id=MATCH.id, name=MATCH.name, meal_type=MATCH.mtype, ingredients=MATCH.reqs, tags=MATCH.tags)
    )
    def match_own_recipe(self, id, name, mtype, reqs, tags, avail):
        missing = reqs - avail
        reason = "Aprobada: Se ajusta a tus preferencias generales y disponibilidad de ingredientes."
        if len(missing) == 0:
            self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="exact", missing_ingredients=frozenset(), reason=reason))
        elif len(missing) <= 2:
            self.declare(EligibleRecipe(id=id, name=name, meal_type=mtype, status="near", missing_ingredients=frozenset(missing), reason=reason))
        else:
            self.declare(ExcludedRecipe(id=id, name=name, reason=f"Dieta general aceptada, pero faltan más de 2 ingredientes ({len(missing)} faltantes)."))

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
    
    eligible, excluded = [], []
    
    # Iteramos de forma segura sobre los valores de la memoria de trabajo
    for fact in engine.facts.values():
        if isinstance(fact, EligibleRecipe):
            fact_id = fact.get("id")
            original = next((r for r in all_recipes if r["id"] == fact_id), None)
            if original:
                eligible.append({
                    "recipe": original,
                    "status": fact.get("status"),
                    "missing_ingredients": list(fact.get("missing_ingredients", [])),
                    "reason": fact.get("reason", "")
                })
        elif isinstance(fact, ExcludedRecipe):
            # Tarea 3: Recolectamos la estructura unificada incluyendo el ID
            excluded.append({
                "id": fact.get("id"),
                "name": fact.get("name"),
                "reason": fact.get("reason")
            })
                
    # Ordenamos: primero las "exact" (0 faltantes), luego por cantidad de faltantes
    eligible.sort(key=lambda x: (0 if x["status"] == "exact" else len(x["missing_ingredients"])))
    
    return {"eligible": eligible, "excluded": excluded}

def plan_menus(eligible_recipes: List[Dict[str, Any]], target: str, all_recipes: List[Dict[str, Any]], selected_meals: Optional[List[str]] = None) -> Dict[str, Any]:
    if isinstance(eligible_recipes, dict) and "eligible" in eligible_recipes:
        eligible_recipes = eligible_recipes["eligible"]
    
    if selected_meals is None:
        selected_meals = ["breakfast", "lunch", "dinner"]
        
    meals_planned = {}
    for mtype in ["breakfast", "lunch", "dinner", "snack"]:
        meals_planned[mtype] = [r for r in eligible_recipes if r["recipe"]["meal_type"] == mtype or (mtype in ["lunch", "dinner"] and r["recipe"]["meal_type"] in ["lunch", "dinner"])]
    
    def get_fallbacks(meal_type: str) -> List[Dict[str, Any]]:
        fallbacks = []
        for r in all_recipes:
            if r["meal_type"] == meal_type or (meal_type in ["lunch", "dinner"] and r["meal_type"] in ["lunch", "dinner"]):
                if not any(el["recipe"]["id"] == r["id"] for el in eligible_recipes):
                    fallbacks.append({
                        "recipe": r,
                        "status": "near",
                        "missing_ingredients": [ing["ingredient_name"] for ing in r["ingredients"]],
                        "reason": "Fallback: Se sugiere para completar el menú, aunque no cumple todas las reglas de la dieta actual."
                    })
        return fallbacks
        
    for mtype in ["breakfast", "lunch", "dinner", "snack"]:
        if not meals_planned[mtype]:
            meals_planned[mtype] = get_fallbacks(mtype)

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
        menu = {}
        for mtype in selected_meals:
            menu[mtype] = pick_meal(meals_planned[mtype], used_ids)
        return {"day_menu": menu, "week_menu": None}
    else:
        week_menu = []
        used_ids = []
        for day in range(1, 8):
            if len(used_ids) > 6:
                used_ids = used_ids[-3:]
            menu = {}
            for mtype in selected_meals:
                menu[mtype] = pick_meal(meals_planned[mtype], used_ids)
            week_menu.append({"day_number": day, "menu": menu})
        return {"day_menu": None, "week_menu": week_menu}
