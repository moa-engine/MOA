from concurrent.futures import ThreadPoolExecutor
from core.engine_loader import EngineLoader
import logging
from fastapi import FastAPI, Query
from typing import Optional
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Loading the engines
loader = EngineLoader()
engine_status = loader.list_engines()

logger.info("Active Engines: %s", engine_status["active"])
logger.warning("Failed Engines: %s", engine_status["failed"])

app = FastAPI()
@app.get("/search")

def search(
    q: Optional[str] = Query(None, description="Search query"),
    engine: Optional[list[str]] = Query(None, description="search engine names default = all"),
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

    results = {}
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
            
            futures[executor.submit(engine_instance.search, **search_params)] = engine_name
        
        for future in futures:
            engine_name = futures[future]
            try:
                data = future.result()
                if size and isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
                    data["results"] = data["results"][:size]

                results[engine_name] = data
            except Exception as e:
                results[engine_name] = {"error": str(e)}
                logger.error("Engine %s failed: %s", engine_name, str(e))

    return results


# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add route for favicon.ico
@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")

