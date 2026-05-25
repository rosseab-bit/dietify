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

def plan_menus(eligible_recipes: List[Dict[str, Any]], target: str, all_recipes: List[Dict[str, Any]], selected_meals: Optional[List[str]] = None) -> Dict[str, Any]:
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
                        "missing_ingredients": [ing["ingredient_name"] for ing in r["ingredients"]]
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
