from abc import ABC, abstractmethod
import json
from pathlib import Path

class BasePlugin(ABC):

    def __init__(self):
        self.config = self.load_config()

    @classmethod
    def load_config(cls):
        config_path = Path(__file__).parent.parent / "configs" / "plugin_params.json"
        try:
            with open(config_path, "r") as f:
                return json.load(f).get(cls.__name__, {})
        except FileNotFoundError:
            return {}

    @abstractmethod
    def run(self, query: str, results: dict) -> dict:
        pass

    def get_params(self) -> dict:
        return self.config.get("params", {})

    def get_type(self) -> str:

        return self.config.get("type", "post")
