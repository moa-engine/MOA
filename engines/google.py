import json
import re
import time
import random
import string
from numbers import Number
from urllib.parse import urlencode, unquote

import requests
from lxml import html
from lxml.etree import _Element, XPath, XPathError

from core.base_engine import BaseEngine


ElementType = _Element
XPathSpecType = str


class SearxEngineXPathException(Exception):
    def __init__(self, xpath_spec, message):
        super().__init__(f"XPath error for '{xpath_spec}': {message}")


_xpath_cache = {}


def get_xpath(xpath_spec: XPathSpecType) -> XPath:
    if not isinstance(xpath_spec, str):
        raise TypeError("xpath_spec must be str")
    if xpath_spec not in _xpath_cache:
        _xpath_cache[xpath_spec] = XPath(xpath_spec)
    return _xpath_cache[xpath_spec]


def eval_xpath(element: ElementType, xpath_spec: XPathSpecType):
    xpath = get_xpath(xpath_spec)
    try:
        return xpath(element)
    except XPathError as e:
        arg = " ".join(str(i) for i in e.args)
        raise SearxEngineXPathException(xpath_spec, arg) from e


def eval_xpath_list(element: ElementType, xpath_spec: XPathSpecType, min_len: int | None = None) -> list:
    result = eval_xpath(element, xpath_spec)
    if not isinstance(result, list):
        raise SearxEngineXPathException(xpath_spec, "the result is not a list")
    if min_len is not None and min_len > len(result):
        raise SearxEngineXPathException(xpath_spec, "len(xpath_str) < " + str(min_len))
    return result


_NOTSET = object()


def eval_xpath_getindex(
    element: ElementType,
    xpath_spec: XPathSpecType,
    index: int,
    default=_NOTSET,
):
    result = eval_xpath_list(element, xpath_spec)
    if -len(result) <= index < len(result):
        return result[index]
    if default == _NOTSET:
        raise SearxEngineXPathException(xpath_spec, "index " + str(index) + " not found")
    return default


def extract_text(
    xpath_results: list[ElementType] | ElementType | str | Number | bool | None,
    allow_none: bool = False,
) -> str | None:
    if isinstance(xpath_results, list):
        result = ""
        for e in xpath_results:
            result = result + (extract_text(e, allow_none=True) or "")
        return result.strip()

    if isinstance(xpath_results, ElementType):
        text = html.tostring(
            xpath_results,
            encoding="unicode",
            method="text",
            with_tail=False,
        )
        text = text.strip().replace("\n", " ")
        return " ".join(text.split())

    if isinstance(xpath_results, (str, Number, bool)):
        return str(xpath_results)

    if xpath_results is None and allow_none:
        return None

    if xpath_results is None and not allow_none:
        raise ValueError("extract_text(None, allow_none=False)")

    raise ValueError("unsupported type")


RE_DATA_IMAGE = re.compile(r'"(data:image/[^"]+)",\s*"([^"]+)"')


class GoogleEngine(BaseEngine):
    def __init__(self):
        super().__init__()
        self.BASE_HEADERS = {
            'Accept-Encoding': 'gzip, deflate',
            'Cache-Control': 'no-cache',
            'DNT': '1',
            'Connection': 'keep-alive',
            "User-Agent": "Mozilla/5.0 (Linux; Android 5.0; SM-G900P Build/LRX21T) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.4509.1584 Mobile Safari/537.36 NSTNWV",
            'Accept-Language': 'fa,fa-IR;q=0.7,en;q=0.3',
            "Accept": "*/*",
        }
        self.GOOGLE_DOMAINS = {
            "US": "www.google.com",
            "CN": "www.google.com.hk",
        }
        self._arcid_random = None
        self._arcid_range = string.ascii_letters + string.digits + "_-"

    def ui_async(self, start: int) -> str:
        """Format of the response from UI's async request."""
        use_ac = "use_ac:true"
        _fmt = "_fmt:prog"

        if not self._arcid_random or (int(time.time()) - self._arcid_random[1]) > 3600:
            self._arcid_random = (
                ''.join(random.choices(self._arcid_range, k=23)),
                int(time.time())
            )
        arc_id = f"arc_id:srp_{self._arcid_random[0]}_1{start:02}"

        return ",".join([arc_id, use_ac, _fmt])

    def parse_url_images(self, text: str):
        data_image_map = {}
        for image_url, img_id in RE_DATA_IMAGE.findall(text):
            data_image_map[img_id] = image_url.encode("utf-8").decode("unicode-escape")
        self.logger.debug("data:image objects --> %s", list(data_image_map.keys()))
        return data_image_map

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

    def search(self, query: str, proxy, timeout: int = 10, page: int = 1, time_range: str = None, safesearch: int = 0, locale="en-US", country="US", **kwargs) -> dict:
        try:
            google_info = self.get_google_info(locale, country)
            offset = (page - 1) * 10
            str_async = self.ui_async(offset)

            params = {
                "q": query,
                **google_info["params"],
                "filter": "0",
                "start": offset,
                # "asearch": "arc",
                # "async": str_async,
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

            data_image_map = self.parse_url_images(response.text)
            dom = html.fromstring(response.text)
            results = []

            for result in eval_xpath_list(dom, '//a[@data-ved and not(@class)]'):
                try:
                    title_tag = eval_xpath_getindex(result, './/div[@style]', 0, default=None)
                    if title_tag is None:
                        self.logger.debug("ignoring item from the result_xpath list: missing title")
                        continue

                    title = extract_text(title_tag)

                    raw_url = result.get("href")
                    if raw_url is None:
                        self.logger.debug(
                            'ignoring item from the result_xpath list: missing url of title "%s"',
                            title,
                        )
                        continue

                    if raw_url.startswith('/url?q='):
                        result_url = unquote(raw_url[7:].split("&sa=U")[0])
                    else:
                        result_url = raw_url

                    content_nodes = eval_xpath(result, '../..//div[contains(@class, "ilUpNd H66NU aSRlid")]')
                    for item in content_nodes:
                        for script in item.xpath(".//script"):
                            parent = script.getparent()
                            if parent is not None:
                                parent.remove(script)

                    content = ""
                    if content_nodes:
                        content = extract_text(content_nodes[0], allow_none=True) or ""

                    xpath_image = eval_xpath_getindex(result, './/img', index=0, default=None)

                    thumbnail = None
                    if xpath_image is not None:
                        thumbnail = xpath_image.get("src")
                        if thumbnail and thumbnail.startswith("data:image"):
                            img_id = xpath_image.get("id")
                            if img_id:
                                thumbnail = data_image_map.get(img_id)

                    if title and result_url and content:
                        results.append({
                            "title": title,
                            "url": result_url,
                            "content": content or "",
                        })

                except Exception as e:
                    self.logger.error(e, exc_info=True)

            return {"results": results}

        except Exception as e:
            self.logger.error(e, exc_info=True)
            return {"results": [], "error": str(e)}
