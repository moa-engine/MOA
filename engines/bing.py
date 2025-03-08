import json
import re
from urllib.parse import urlencode
from lxml import html
import requests
from core.base_engine import BaseEngine

class BingEngine(BaseEngine):
    def __init__(self):
        super().__init__()
        self.BASE_HEADERS = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "*/*",
        }
        self.BING_DOMAINS = {
            "US": "www.bing.com",
            "CN": "cn.bing.com",
        }

    def detect_bing_sorry(self, response):
        if "captcha" in response.url:
            raise Exception("Bing CAPTCHA detected")

    def get_bing_info(self, locale="en-US", country="US"):
        lang_code = locale.split("-")[0]
        return {
            "subdomain": self.BING_DOMAINS.get(country.upper(), "www.bing.com"),
            "params": {
                "setlang": lang_code,
                "mkt": f"{lang_code}-{country}",
                "ie": "UTF-8",
                "oe": "UTF-8",
            },
            "headers": self.BASE_HEADERS,
            "cookies": {"CONSENT": "YES+"},
        }

    def search(self, query: str, timeout: int = 10, page: int = 1, time_range: str = None, safesearch: int = 0, locale="en-US", country="US") -> dict:
        try:
            bing_info = self.get_bing_info(locale, country)
            offset = (page - 1) * 10
            params = {
                "q": query,
                "first": offset,
                **bing_info["params"],
            }

            time_range_dict = {"day": "d", "week": "w", "month": "m", "year": "y"}
            if time_range in time_range_dict:
                params["tbs"] = f"qdr:{time_range_dict[time_range]}"

            safesearch_mapping = {0: "off", 1: "medium", 2: "high"}
            params["safe"] = safesearch_mapping.get(safesearch, "off")

            url = f"https://{bing_info['subdomain']}/search?{urlencode(params)}"
            response = requests.get(
                url,
                headers=bing_info["headers"],
                cookies=bing_info["cookies"],
                timeout=timeout
            )

            response.raise_for_status()
            self.detect_bing_sorry(response)

            dom = html.fromstring(response.text)
            results = []

            for result in dom.xpath('//li[contains(@class, "b_algo")]'):
                title = result.xpath('.//h2//text()')
                url = result.xpath('.//h2/a/@href')
                content = result.xpath('.//p//text()')

                if title and url and content:
                    results.append({
                        "title": " ".join(title).strip(),
                        "url": url[0],
                        "content": " ".join(content).strip(),
                    })

            return {"results": results}
        
        except Exception as e:
            return {"error": str(e)}
