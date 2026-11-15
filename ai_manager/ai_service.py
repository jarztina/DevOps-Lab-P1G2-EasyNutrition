from abc import ABC, abstractmethod

class AIService(ABC):
    @abstractmethod
    def analyse_image(self, image_bytes: bytes, media_type: str) -> tuple[bool, dict | str]:
        pass

    @abstractmethod
    def search_recipes(self, ingredient_names: list[str]) -> tuple[bool, list | str]:
        pass

    @abstractmethod
    def pick_query_ingredients(self, items: list) -> list[str]:
        pass
    