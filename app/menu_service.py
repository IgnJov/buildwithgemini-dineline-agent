# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Public Menu & Recipe service for DineLine AI using TheMealDB open API."""

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List


def search_specials_and_menu(query: str = "") -> List[Dict[str, Any]]:
    """Searches live dish specials, ingredients, and menu items via TheMealDB public API.

    Supports optional MEALDB_API_KEY environment variable (defaults to free tier '1').
    """
    api_key = os.getenv("MEALDB_API_KEY", "1")
    
    if query.strip():
        encoded = urllib.parse.quote(query.strip())
        url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php?s={encoded}"
    else:
        # Default recommendations if no specific keyword
        url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php?s=pasta"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DineLineAI-Agent/1.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                meals = payload.get("meals") or []
                
                curated = []
                for m in meals[:5]:  # Return top 5 items
                    ingredients = []
                    for i in range(1, 6):
                        ing = m.get(f"strIngredient{i}")
                        if ing and ing.strip():
                            ingredients.append(ing.strip())

                    curated.append({
                        "dish_name": m.get("strMeal"),
                        "category": m.get("strCategory"),
                        "cuisine_origin": m.get("strArea"),
                        "image_url": m.get("strMealThumb"),
                        "highlighted_ingredients": ingredients,
                        "description": (m.get("strInstructions") or "")[:140] + "...",
                    })
                return curated
    except Exception as e:
        return [{"error": f"Failed to fetch live menu specials: {str(e)}"}]

    return []
