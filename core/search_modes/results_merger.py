from collections import defaultdict


def results_merger(out_results):
    flattened_result = {}
    index = 0

    # Combine results of all engines
    for engine_name, engine_data in out_results.items():
        if "results" in engine_data and isinstance(engine_data["results"], list):
            for result in engine_data["results"]:
                if isinstance(result, dict):
                    result_with_engine = result.copy()
                    result_with_engine["engine"] = engine_name
                    flattened_result[index] = result_with_engine
                    index += 1

    # Remove results without title or URL
    keys_to_delete = []
    for key, result in flattened_result.items():
        if not result.get("title") or not result.get("url"):
            keys_to_delete.append(key)
    for key in keys_to_delete:
        del flattened_result[key]

    # Reset keys to be in order
    results_without_blanks = {i: v for i, v in enumerate(flattened_result.values())}

    # Group by URL
    duplicates = defaultdict(list)
    for key, result in results_without_blanks.items():
        url = result.get("url")
        if url:
            duplicates[url].append(key)

    new_flattened_result = {}

    for url, keys in duplicates.items():
        if len(keys) == 1:
            # Only one result for this URL
            key = keys[0]
            new_flattened_result[key] = results_without_blanks[key]
        else:
            # Multiple results: pick best title (longest)
            titles = {key: results_without_blanks[key].get("title", "") for key in keys}
            max_key = max(titles, key=lambda k: len(titles[k]))
            best_result = results_without_blanks[max_key].copy()

            # Combine engine names from all results
            engine_names = set()
            # Engine of best result
            orig_engine = best_result.get("engine")
            if isinstance(orig_engine, list):
                engine_names.update(orig_engine)
            elif isinstance(orig_engine, str):
                engine_names.add(orig_engine)

            # Engines of the rest
            for key in keys:
                if key == max_key:
                    continue
                other_engine = results_without_blanks[key].get("engine")
                if isinstance(other_engine, list):
                    engine_names.update(other_engine)
                elif isinstance(other_engine, str):
                    engine_names.add(other_engine)

            # Set combined engine(s)
            if len(engine_names) == 1:
                best_result["engine"] = next(iter(engine_names))
            else:
                best_result["engine"] = list(engine_names)

            new_flattened_result[max_key] = best_result

    # Reindex the final result
    sorted_results = {i: v for i, v in enumerate(new_flattened_result.values())}

    return sorted_results
