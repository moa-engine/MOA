import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from core.engine_loader import EngineLoader
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="SearXNG-Like Multi-Engine Search")
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument("-e", "--engines", nargs="+", help="List of engines (default: all)")
    parser.add_argument("-p", "--page", type=int, default=1, help="Page number")
    parser.add_argument("-s", "--safesearch", type=int, choices=[0, 1, 2], default=0, help="Safe search level")
    parser.add_argument("-t", "--time_range", choices=["day", "week", "month", "year"], help="Time range filter")
#    parser.add_argument("-n", "--num_results", type=int, default=10, help="Number of results per engine")
    
    args = parser.parse_args()
    
    loader = EngineLoader()
    engine_status = loader.list_engines()
    
    logger.info("Active Engines: %s", engine_status["active"])
    logger.warning("Failed Engines: %s", engine_status["failed"])
    
    selected_engines = args.engines if args.engines else engine_status["active"]
    
    results = {}
    with ThreadPoolExecutor() as executor:
        futures = {}
        for engine_name in selected_engines:
            engine = loader.get_engine(engine_name)
            if not engine:
                logger.error("Engine %s not found!", engine_name)
                continue
            
            search_params = {
                "query": args.query,
                "page": args.page,
                "safesearch": args.safesearch,
                "time_range": args.time_range,
 #               "num_results": args.num_results,
            }
            
            futures[executor.submit(engine.search, **search_params)] = engine_name
        
        for future in futures:
            engine_name = futures[future]
            try:
                results[engine_name] = future.result()
            except Exception as e:
                results[engine_name] = {"error": str(e)}
                logger.error("Engine %s failed: %s", engine_name, str(e))
    
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
