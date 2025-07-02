from core.base_engine import BaseEngine
import requests
import re
from urllib.parse import urlencode, quote_plus
from lxml import html
from proxy_utils import get_proxy_config


proxies = get_proxy_config(enabled=True)

class DuckDuckGoEngine(BaseEngine):

    def __init__(self):
        super().__init__()
        self.time_range_dict = {'day': 'd', 'week': 'w', 'month': 'm', 'year': 'y'}
        self.base_url = "https://html.duckduckgo.com/html"

    def search(self, query: str,timeout: int = 10 , page: int = 1, time_range: str = None, safesearch: int = 0, **kwargs) -> dict:
        params = {
            "page": page,
            "safesearch": safesearch,
            "time_range": time_range,
            **self.get_params(),
            **kwargs
        }

        try:
            if len(query) >= 500:
                return {"error": "Query too long (max 500 chars)"}

            data = {
                "q": query,
                "kl": self.config.get("region", "wt-wt"),
                "df": self.time_range_dict.get(params["time_range"], ""),
                "s": (params["page"] - 1) * 30
            }

            response = requests.post(
                self.base_url,
                data=data,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=self.config.get("timeout", timeout),
                proxies=proxies
            )
            response.raise_for_status()

            dom = html.fromstring(response.text)
            results = []

            for result in dom.xpath('//div[contains(@class, "web-result")]'):
                title = result.xpath('.//h2/a/text()')
                url = result.xpath('.//h2/a/@href')
                content = result.xpath('.//a[contains(@class, "result__snippet")]//text()')

                if title and url and content:
                    results.append({
                        "title": " ".join(title).strip(),
                        "url": url[0].split("//duckduckgo.com/?q=")[-1],
                        "content": " ".join(content).strip()
                    })

            return {"results": results}

        except Exception as e:
            return {"error": str(e)}
