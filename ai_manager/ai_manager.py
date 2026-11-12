import logging
import time

from .ai_service import AIService
from .ingredient_parser import IngredientParser
from .recipe_source import RecipeSource, SpoonacularSource
from .vision_client import VisionClient

logger = logging.getLogger(__name__)

class AIManager(AIService):
    MAX_ATTEMPTS = 3
    MAX_QUERY_INGREDIENTS = 5

    def __init__(
        self,
        vision: VisionClient | None = None,
        parser: IngredientParser | None = None,
        recipe_source: RecipeSource | None = None,
        sleep=time.sleep,
    ):
        # Composition: the manager is built from smaller parts it uses.
        self._vision = vision or VisionClient()
        self._parser = parser or IngredientParser()
        # Aggregation: any RecipeSource can be plugged in (Spoonacular today).
        self._recipes = recipe_source or SpoonacularSource()
        self._sleep = sleep

    def identify_ingredients(
        self, image_bytes: bytes, media_type: str
    ) -> tuple[bool, list | str]:
        prompt = self._vision.build_prompt()
        last_error = "unknown error"
        
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            ok, raw = self._vision.ask(image_bytes, media_type, prompt)
            if not ok:
                last_error = raw
                logger.warning("AI attempt %d/%d failed: %s", attempt, self.MAX_ATTEMPTS, raw)
                self._sleep(attempt)
                continue
                
            ok, result = self._parser.parse(raw)
            if ok:
                return True, result
                
            last_error = result
            logger.warning("AI attempt %d/%d gave a bad answer: %s",
                           attempt, self.MAX_ATTEMPTS, result)
                           
        return False, f"The AI service failed after {self.MAX_ATTEMPTS} tries: {last_error}"

    def pick_query_ingredients(self, items: list) -> list[str]:
        """Take the most confident ingredient names (no duplicates), best first."""
        ranked = sorted(items, key=lambda i: i.get("confidence", 0), reverse=True)
        names = []
        for item in ranked:
            name = str(item.get("name", "")).strip().lower()
            if name and name not in names:
                names.append(name)
        return names[:self.MAX_QUERY_INGREDIENTS]

    def search_recipes(self, ingredient_names: list[str]) -> tuple[bool, list | str]:
        return self._recipes.find_recipes(ingredient_names)

    def analyse_image(self, image_bytes: bytes, media_type: str) -> tuple[bool, dict | str]:
        """Photo in, ai_data out: detected ingredients + candidate recipes."""
        ok, items = self.identify_ingredients(image_bytes, media_type)
        if not ok:
            return False, items
            
        ok, recipes = self.search_recipes(self.pick_query_ingredients(items))
        if not ok:
            return False, recipes
            
        return True, {"detected_items": items, "recipes": recipes}
