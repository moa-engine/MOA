import yaml
from pathlib import Path

def load_config():
    config_path = Path(__file__).parent.parent / "configs" / "config.yml"
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    except FileNotFoundError:
        return {}
