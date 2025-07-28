import json
import re
from urllib.parse import urlencode
from lxml import html
import requests
import random
import string
import time
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
        self._arcid_random = None
        self._arcid_range = string.ascii_letters + string.digits + "_-"

    def ui_async(self, start: int) -> str:
        """Format of the response from UI's async request.

        - ``arc_id:<...>,use_ac:true,_fmt:prog``

        The arc_id is random generated every hour.
        """
        use_ac = "use_ac:true"
        # _fmt:html returns a HTTP 500 when user search for celebrities like
        # '!google natasha allegri' or '!google chris evans'
        _fmt = "_fmt:prog"

        # create a new random arc_id every hour
        if not self._arcid_random or (int(time.time()) - self._arcid_random[1]) > 3600:
            self._arcid_random = (''.join(random.choices(self._arcid_range, k=23)), int(time.time()))
        arc_id = f"arc_id:srp_{self._arcid_random[0]}_1{start:02}"

        return ",".join([arc_id, use_ac, _fmt])

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

    def search(self, query: str, proxy, timeout: int = 10 , page: int = 1, time_range: str = None, safesearch: int = 0, locale="en-US", country="US", **kwargs) -> dict:
        try:
            google_info = self.get_google_info(locale, country)
            offset = (page - 1) * 10
            str_async = self.ui_async(offset)
            params = {
                "q": query,
                **google_info["params"],
                'filter': '0',
                "start": offset,
                "asearch": "arc",
                "async": str_async,
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
                timeout=timeout,
                proxies=proxy
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
