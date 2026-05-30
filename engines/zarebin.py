
# about
# "website": 'https://zarebin.ir/'
# "official_api_documentation": ''
# "use_official_api": True
# "require_api_key": False
# "results": 'JSON'
# categories = ['general']
# language_support = False

from core.base_engine import BaseEngine
import requests
from urllib.parse import quote_plus

class Zarebin(BaseEngine):

    def __init__(self):
        super().__init__()
        self.base_url = 'https://zarebin.ir/gse/api/'
        self.search_url = self.base_url + 'search?q={query}&pl=0&page={page}&ldi=0&user_device=d&limit={limit}&enable_smart_answers=true&qsrc=normal'

    def search(self, query: str, proxy, timeout: int = 10 , page: int = 1, time_range: str = None, safesearch: int = 0, limit = 10, **kwargs) -> dict:
        try:
            url= self.search_url.format(query=quote_plus(query), limit=limit, page=page)

            if len(query) >= 500:
                return {"error": "Query too long (max 500 chars)"}


            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0", "Accept":"application/json"},
                timeout=self.config.get("timeout", timeout),
                proxies=proxy
            )
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()
            if "json" not in content_type:
                raise Exception("Response is not JSON")

            try:
                search_results = response.json()
            except ValueError as e:
                raise Exception("Invalid JSON from zarebin") from e

            results = []

            webs = (
            search_results.get("result", {})
                .get("all", {})
                .get("results", {})
                .get("webs", [])
            )


            # parse results
            for result in webs:
                # append result
                results.append(
                    {
                        'url': result.get('web_link'),
                        'title': result.get('title'),
                        'content': result.get('description'),
                    }
                )

            # return results
            return {"results": results}
        except Exception as e:
            self.logger.error(e, exc_info=True)
            return {"results": [], "error": str(e)}
