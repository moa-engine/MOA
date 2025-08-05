import asyncio
import json
from fastapi.responses import StreamingResponse

async def stream_search(
    selected_engines,
    loader,
    search_params,
    limit,
    selected_pre_plugins,
    selected_post_plugins,
    q,
    ):
    async def event_stream():
        queue = asyncio.Queue()

        counter = {"value": 0}
        async def run_tasks():
            tasks = []

            for eng_name in selected_engines:
                engine_instance = loader.get_engine(eng_name)
                if not engine_instance:
                    await queue.put({"type": "engine_result", "name": eng_name, "error": "Engine not found"})
                    continue

                async def run_engine(name, instance):
                    try:
                        result = await asyncio.to_thread(
                            instance.search, **search_params)
                        if isinstance(result, dict) and "results" in result:
                            if limit:
                                result["results"] = result["results"][:limit]
                            counter["value"] += len(result["results"])
                        await queue.put({"type": "engine_result", "name": name, "result": result})
                    except Exception as e:
                        await queue.put({"type": "engine_result", "name": name, "error": str(e)})

                tasks.append(run_engine(eng_name, engine_instance))

            for pre_plugin in selected_pre_plugins:
                plugin_name = pre_plugin.__class__.__name__

                async def run_pre_plugin(instance, name):
                    try:
                        result = await asyncio.to_thread(instance.run, q)
                        await queue.put({"type": "pre_plugin_result", "name": name, "result": result})
                    except Exception as e:
                        await queue.put({"type": "pre_plugin_result", "name": name, "error": str(e)})

                tasks.append(run_pre_plugin(pre_plugin, plugin_name))

            await asyncio.gather(*tasks)

            for post_plugin in selected_post_plugins:
                plugin_name = post_plugin.__class__.__name__
                try:
                    result = await asyncio.to_thread(post_plugin.run, q)
                    await queue.put({"type": "post_plugin_result", "name": plugin_name, "result": result})
                except Exception as e:
                    await queue.put({"type": "post_plugin_result", "name": plugin_name, "error": str(e)})

            await queue.put({"type": "number_of_results", "data": counter["value"]})
            await queue.put({"type": "done", "data": "[DONE]"})

        asyncio.create_task(run_tasks())

        while True:
            data = await queue.get()
            if data.get("type") == "done":
                yield json.dumps(data).encode() + b"\n"
                break
            yield json.dumps(data).encode() + b"\n"

    return StreamingResponse(event_stream(), media_type="application/json")
