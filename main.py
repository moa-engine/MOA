from core.engine_loader import EngineLoader
from core.plugin_loader import PluginLoader
from core.config_loader import load_config
from core.search_modes.normal import normal_search
from core.search_modes.stream import stream_search
from core.search_modes.results_merger import results_merger
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import logging
import asyncio
import json
import os


# Load settings from configs/config.yml
configs = load_config()

log_level_str = configs.get("logging_level", "INFO").upper()
logging_level = getattr(logging, log_level_str, logging.INFO)

# Start logging
logging.basicConfig(level=logging_level)
logger = logging.getLogger(__name__)

# Determine the value of max_threads for ThreadPoolExecutor
if configs["auto_max_threads"]:
    max_threads = min(32, (os.cpu_count() or 4) * 2)
else:
    max_threads = configs["max_threads"]

# Loading the engines and plugins
ploader = PluginLoader()
loader = EngineLoader()
engine_status = loader.list_engines()
plugin_status = ploader.list_plugins()

# Show engines in each category
for types in engine_status:
    logger.info(f"{types} Engines: %s", engine_status[types])

# Show healthy and faulty plugins
logger.info("Active Plugins: %s", plugin_status["active"])
logger.warning("Failed Plugins: %s", plugin_status["failed"])


def get_proxy_config(proxy: dict) -> dict:
    """
    Converts proxy configuration from YAML into a format usable by the 'requests' library.
    Example input:
        {
            "http": "http://127.0.0.1:8080",
            "https": "http://127.0.0.1:8080"
        }
    """
    if not isinstance(proxy, dict):
        raise TypeError("Proxy config must be a dictionary.")

    output_proxy = {}

    for key in ("http", "https"):
        value = proxy.get(key)
        if value:
            if not (value.startswith("http://") or value.startswith("https://")):
                raise ValueError(f"{key} proxy must start with http:// or https://")
            output_proxy[key] = value

    return output_proxy if output_proxy else None


if configs["enabled_proxy"]:
    proxy = get_proxy_config(configs["proxys"])
else:
    proxy = {}


app = FastAPI()
@app.get("/search")

async def search(
    q: Optional[str] = Query(None, description="Search query"),
    engines: Optional[list[str]] = Query(configs["active_engines"], description="search engine names default = all"),
    enabled_plugins: Optional[list[str]] = Query(configs["active_plugins"], description="plugin names default = all"),
    time_range: Optional[str] = Query("", description="Time range filter"),
    language: Optional[str] = Query(configs["language"], description="search language "),
    limit: Optional[int] = Query(configs["limit"], description="Number of results per engine default all results"),
    pageno: int = Query(configs["pageno"], description="pageno number"),
    safesearch: int = Query(configs["safesearch"], description="Safe search level"),
    country: str = Query(configs["country"], description="Country to search"),
    categories: str = Query(configs["default_category"], description="# The default category for which results are requested."),
    api_mode: str = Query(configs["api_mode"], description="API behavior. stream, normal or merged"),
    ):
    # Send error if input query is missing
    if not q:
        raise HTTPException(status_code=400, detail="Search query input cannot be empty.")


    categories = categories.lower() if categories else "general"
    if categories not in engine_status:
        categories = "general"

    if engines:
        if categories in engine_status:
            invalid_engines = [e for e in engines if e not in engine_status[categories]]
            if invalid_engines:
                return {
                    "error": f"Engine(s) {invalid_engines} not found in category '{categories}'"
                }
        selected_engines = engines
    else:
        # If no engine is given, use category
        selected_engines = engine_status[categories]

    # Determining and validating pre and post plugins
    selected_pre_plugins = []
    selected_post_plugins = []

    if enabled_plugins:
        for plugin_name in enabled_plugins:
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

    # Creating search parameters
    search_params = {
        "query": q,
        "page": pageno,
        "safesearch": safesearch,
        "time_range": time_range,
        "num_results": limit, # For engines that can return a certain number of results by default
        "locale": language,
        "country": country,
        "proxy": proxy
    }

    # Normal api mode takes all results from all engines. Then sends them all at once.
    if api_mode == "normal":
        results, pre_plugin_outputs = normal_search(
            max_threads=max_threads,
            selected_engines=selected_engines,
            loader=loader,
            logger=logger,
            search_params=search_params,
            selected_pre_plugins=selected_pre_plugins,
            q=q,
            limit=limit,)

        number_of_results = 0
        for engine_data in results.values():
            if isinstance(engine_data, dict) and "results" in engine_data and isinstance(engine_data["results"], list):
                number_of_results += len(engine_data["results"])

        return {
            "number_of_results" : number_of_results,
            "results": results,
            "pre_plugins": pre_plugin_outputs
            }


    # In streaming API mode, the results of engines and pre-plugins are executed in parallel and sent separately to the client without delay.
    elif api_mode == "stream":
        return await stream_search(
            selected_engines=selected_engines,
            loader=loader,
            search_params=search_params,
            limit=limit,
            selected_pre_plugins=selected_pre_plugins,
            selected_post_plugins=selected_post_plugins,
            q=q,
        )

    elif api_mode == "merged":
        results, pre_plugin_outputs = normal_search(
            max_threads=max_threads,
            selected_engines=selected_engines,
            loader=loader,
            logger=logger,
            search_params=search_params,
            selected_pre_plugins=selected_pre_plugins,
            q=q,
            limit=limit,)
        results = results_merger(results)
        number_of_results = len(results)
        return {
            "number_of_results" : number_of_results,
            "results": results,
            "pre_plugins": pre_plugin_outputs
            }

    else:
        return "api_mode should be normal, stream or merged."

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add route for favicon.ico
@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")

@app.get("/")
async def root():
    return JSONResponse({
        "message": "Welcome to MOA search API. Use /search endpoint with appropriate parameters."
    })
