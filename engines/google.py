import json
import re
from urllib.parse import urlencode
from lxml import html
import requests
from core.base_engine import BaseEngine

class GoogleEngine(BaseEngine):
    def __init__(self):
        super().__init__()
        self.BASE_HEADERS = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "*/*",
        }
        self.GOOGLE_DOMAINS = {
            "US": "www.google.com",
            "CN": "www.google.com.hk",
        }

    def detect_google_sorry(self, response):
        if "sorry.google.com" in response.url or "/sorry" in response.url:
            raise Exception("Google CAPTCHA detected")

    def get_google_info(self, locale="en-US", country="US"):
        lang_code = locale.split("-")[0]
        return {
            "subdomain": self.GOOGLE_DOMAINS.get(country.upper(), "www.google.com"),
            "params": {
                "hl": f"{lang_code}-{country}",
                "lr": f"lang_{lang_code}",
                "cr": f"country{country}" if country else "",
                "ie": "utf8",
                "oe": "utf8",
            },
            "headers": self.BASE_HEADERS,
            "cookies": {"CONSENT": "YES+"},
        }

    def search(self, query: str,timeout: int = 10 , page: int = 1, time_range: str = None, safesearch: int = 0, locale="en-US", country="US") -> dict:
        try:
            google_info = self.get_google_info(locale, country)
            offset = (page - 1) * 10
            params = {
                "q": query,
                "start": offset,
                "asearch": "arc",
                "async": "use_ac:true,_fmt:prog",
                **google_info["params"],
            }

            time_range_dict = {"day": "d", "week": "w", "month": "m", "year": "y"}
            if time_range in time_range_dict:
                params["tbs"] = f"qdr:{time_range_dict[time_range]}"

            safesearch_mapping = {0: "off", 1: "medium", 2: "high"}
            params["safe"] = safesearch_mapping.get(safesearch, "off")

            url = f"https://{google_info['subdomain']}/search?{urlencode(params)}"
            response = requests.get(
                url,
                headers=google_info["headers"],
                cookies=google_info["cookies"],
                timeout=timeout
            )
            response.raise_for_status()
            self.detect_google_sorry(response)

            dom = html.fromstring(response.text)
            results = []

            for result in dom.xpath('//div[contains(@jscontroller, "SC7lYd")]'):
                title = result.xpath('.//a/h3//text()')
                url = result.xpath('.//a[h3]/@href')
                content = result.xpath('.//div[contains(@data-sncf, "1")]//text()')

                if title and url and content:
                    results.append({
                        "title": " ".join(title).strip(),
                        "url": url[0].split("&sa=U&")[0],  # پاکسازی URL
                        "content": " ".join(content).strip(),
                    })

            return {"results": results}

        except Exception as e:
            return {"error": str(e)}
