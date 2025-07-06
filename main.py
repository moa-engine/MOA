from concurrent.futures import ThreadPoolExecutor
from core.engine_loader import EngineLoader
from core.plugin_loader import PluginLoader
import logging
from fastapi import FastAPI, Query
from typing import Optional
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Loading the engines and plugins
ploader = PluginLoader()
loader = EngineLoader()
engine_status = loader.list_engines()
plugin_status = ploader.list_plugins()

logger.info("Active Engines: %s", engine_status["active"])
logger.warning("Failed Engines: %s", engine_status["failed"])

logger.info("Active Plugins: %s", plugin_status["active"])
logger.warning("Failed Plugins: %s", plugin_status["failed"])


app = FastAPI()
@app.get("/search")

def search(
    q: Optional[str] = Query(None, description="Search query"),
    engine: Optional[list[str]] = Query(None, description="search engine names default = all"),
    plugin: Optional[list[str]] = Query(None, description="search engine names default = all"),
    time_range: Optional[str] = Query("", description="Time range filter"),
    lang: Optional[str] = Query("", description="search language "),
    size: Optional[int] = Query(None, description="Number of results per engine default all results"),
    page: int = Query(1, description="Page number"),
    safesearch: int = Query(0, description="Safe search level"),
    country: str = Query("", description="Country to search"),
#    category: str = Query("", description="")
    ):

    if q == None:
        return "Search query input cannot be empty."

    selected_engines = engine if engine else engine_status["active"] # Using active engines in the absence of engine input

    selected_pre_plugins = []
    selected_post_plugins = []

    if plugin:
        for plugin_name in plugin:
            plugin_instance = ploader.get_plugin(plugin_name)
            if not plugin_instance:
                logger.warning("Plugin '%s' not found or failed to load.", plugin_name)
                continue

            plugin_type = plugin_instance.get_type().lower()
            if plugin_type == "pre":
                selected_pre_plugins.append(plugin_instance)
            elif plugin_type == "post":
                selected_post_plugins.append(plugin_instance)
            else:
                logger.warning("Plugin '%s' has unknown type '%s'", plugin_name, plugin_type)
    else:
        selected_pre_plugins = ploader.pre_plugins
        selected_post_plugins = ploader.post_plugins

    results = {}
    pre_plugin_outputs = {}

    with ThreadPoolExecutor() as executor:
        futures = {}
        for engine_name in selected_engines:
            engine_instance = loader.get_engine(engine_name)
            if not engine_instance:
                logger.error("Engine %s not found!", engine_name)
                continue
            
            search_params = {
                "query": q,
                "page": page,
                "safesearch": safesearch,
                "time_range": time_range,
                "num_results": size, # For engines that can return a certain number of results by default
                "locale": lang,
                "country": country,
#                "category": category

            }
            
            futures[executor.submit(engine_instance.search, **search_params)] = ("engine", engine_name)

        for plugin in selected_pre_plugins:
            futures[executor.submit(plugin.run, q)] = ("pre_plugin", plugin.__class__.__name__)

        for future in futures:
            ftype, name = futures[future]
            try:
                output = future.result()
                if ftype == "engine":
                    if size and isinstance(output, dict) and "results" in output and isinstance(output["results"], list):
                        output["results"] = output["results"][:size]
                    results[name] = output
                elif ftype == "pre_plugin":
                    pre_plugin_outputs[name] = output
            except Exception as e:
                logger.error("%s %s failed: %s", ftype.capitalize(), name, str(e))
                if ftype == "engine":
                    results[name] = {"error": str(e)}
                elif ftype == "pre_plugin":
                    pre_plugin_outputs[name] = {"error": str(e)}

    return {
        "results": results,
        "pre_plugins": pre_plugin_outputs
    }

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add route for favicon.ico
@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")

