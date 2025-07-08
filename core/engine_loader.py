import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Type
from core.base_engine import BaseEngine
import logging

logger = logging.getLogger(__name__)

class EngineLoader:
    
    def __init__(self):
        self.engines: Dict[str, BaseEngine] = {}
        self.valid_engines = []
        self.failed_engines = []
        self.general_engines = []
        self.images_engines = []
        self.videos_engines = []
        self.news_engines = []
        self.books_engines = []
        self.maps_engines = []
        self.shaping_engines = []
        self.other_engines = []

        self.category_map = {
            "general": self.general_engines,
            "images": self.images_engines,
            "videos": self.videos_engines,
            "news": self.news_engines,
            "books": self.books_engines,
            "maps": self.maps_engines,
            "shaping": self.shaping_engines,
        }

        self.load_engines()

    
    def load_engines(self):
        engines_dir = Path(__file__).parent.parent / "engines"
        
        for module_path in engines_dir.glob("*.py"):
            if module_path.name == "__init__.py":
                continue
            
            module_name = module_path.stem
            try:
                module = importlib.import_module(f"engines.{module_name}")
                engine_class = None
                
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseEngine)
                        and attr != BaseEngine
                    ):
                        engine_class = attr
                        break
                
                if not engine_class:
                    raise AttributeError("No valid engine class found")
                
                engine_id = engine_class.__name__.replace("Engine", "").lower()
                instance = engine_class()
                self.engines[engine_id] = instance
                self.valid_engines.append(engine_id)

                engine_type = instance.get_type().lower()
                target_list = self.category_map.get(engine_type, self.other_engines)
                target_list.append(engine_id)


            except Exception as e:
                self.failed_engines.append(module_name)
                logger.error("Engine %s failed: %s", module_name, str(e))
    
    def list_engines(self):
        return {
            "active": self.valid_engines,
            "failed": self.failed_engines,
            "general": self.general_engines,
            "images": self.images_engines,
            "videos": self.videos_engines,
            "news": self.news_engines,
            "books": self.books_engines,
            "maps": self.maps_engines,
            "shaping": self.shaping_engines,
            "other": self.other_engines,
        }
    
    def get_engine(self, name: str) -> BaseEngine | None:
        return self.engines.get(name.lower())
