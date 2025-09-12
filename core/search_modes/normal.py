# add selected_post_plugins
from concurrent.futures import ThreadPoolExecutor

def normal_search(
    max_threads,
    selected_engines,
    loader,
    logger,
    search_params,
    selected_pre_plugins,
    selected_post_plugins,
    q,
    limit,
    ):
    results = {}
    pre_plugin_outputs = {} # Pre plugins also work in parallel with engines.

    with ThreadPoolExecutor(max_threads) as executor:
        futures = {}
        for engine_name in selected_engines:
            engine_instance = loader.get_engine(engine_name)
            if not engine_instance:
                logger.error("Engine %s not found!", engine_name)
                continue

            futures[executor.submit(engine_instance.search, **search_params)] = ("engine", engine_name)

        for plugin in selected_pre_plugins:
            futures[executor.submit(plugin.run, q)] = ("pre_plugin", plugin.__class__.__name__)

        for future in futures:
            ftype, name = futures[future]
            try:
                output = future.result()
                if ftype == "engine":
                    if limit and isinstance(output, dict) and "results" in output and isinstance(output["results"], list):
                        output["results"] = output["results"][:limit]
                    results[name] = output
                elif ftype == "pre_plugin":
                    pre_plugin_outputs[name] = output
            except Exception as e:
                logger.error("%s %s failed: %s", ftype.capitalize(), name, str(e))
                if ftype == "engine":
                    results[name] = {"error": str(e)}
                elif ftype == "pre_plugin":
                    pre_plugin_outputs[name] = {"error": str(e)}
    post_plugin_outputs = {}
    with ThreadPoolExecutor(max_threads) as executor:
        post_futures = {
            executor.submit(post_plugin.run, q, results): post_plugin.__class__.__name__
            for post_plugin in selected_post_plugins
        }

        for future in post_futures:
            output = future.result()
            post_plugin_outputs[post_futures[future]] = output

    return results, pre_plugin_outputs, post_plugin_outputs
