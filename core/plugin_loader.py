import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Type
from core.base_plugin import BasePlugin
import logging

logger = logging.getLogger(__name__)

class PluginLoader:

    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
        self.valid_plugins = []
        self.failed_plugins = []
        self.post_plugins = []
        self.pre_plugins = []
        self.load_plugins()

    def load_plugins(self):
        plugins_dir = Path(__file__).parent.parent / "plugins"

        for module_path in plugins_dir.glob("*.py"):
            if module_path.name == "__init__.py":
                continue

            module_name = module_path.stem
            try:
                module = importlib.import_module(f"plugins.{module_name}")
                plugin_class = None

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BasePlugin)
                        and attr != BasePlugin
                    ):
                        plugin_class = attr
                        break

                if not plugin_class:
                    raise AttributeError("No valid plugin class found")

                plugin_id = plugin_class.__name__.replace("plugin", "").lower()

                instance = plugin_class()
                self.plugins[plugin_id] = instance
                self.valid_plugins.append(plugin_id)

                plugin_type = instance.get_type().lower()
                if plugin_type == "pre":
                    self.pre_plugins.append(instance)
                elif plugin_type == "post":
                    self.post_plugins.append(instance)
                else:
                    logger.warning("Unknown plugin type '%s' in %s", plugin_type, plugin_id)

            except Exception as e:
                self.failed_plugins.append(module_name)
                logger.error("plugin %s failed: %s", module_name, str(e))

    def list_plugins(self):
        return {
            "active": self.valid_plugins,
            "failed": self.failed_plugins,
            "post" : self.post_plugins,
            "pre" : self.pre_plugins
        }

    def get_plugin(self, name: str) -> BasePlugin | None:
        return self.plugins.get(name.lower())
