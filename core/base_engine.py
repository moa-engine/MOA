import yaml
from pathlib import Path
from abc import ABC, abstractmethod

class BaseEngine(ABC):
    
    def __init__(self):
        self.config = self.load_config()
    
    @classmethod
    def load_config(cls):
        config_path = Path(__file__).parent.parent / "configs" / "engine_params.yml"
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f).get(cls.__name__, {})
        except FileNotFoundError:
            return {}
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> dict:
        pass
    
    def get_params(self) -> dict:
        return self.config.get("params", {})

    def get_type(self) -> str:

        return self.config.get("type", "general")
