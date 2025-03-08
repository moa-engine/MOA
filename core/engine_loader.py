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
                self.engines[engine_id] = engine_class()
                self.valid_engines.append(engine_id)
                
            except Exception as e:
                self.failed_engines.append(module_name)
                logger.error("Engine %s failed: %s", module_name, str(e))
    
    def list_engines(self):
        return {
            "active": self.valid_engines,
            "failed": self.failed_engines
        }
    
    def get_engine(self, name: str) -> BaseEngine | None:
        return self.engines.get(name.lower())
