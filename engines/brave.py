from urllib.parse import urlencode
from lxml import html
import requests
from core.base_engine import BaseEngine
from dateutil import parser

class BraveEngine(BaseEngine):
    def __init__(self):
        super().__init__()
        self.base_url = "https://search.brave.com/"
        self.category_map = {
            'search': 'search',
            'images': 'images',
            'videos': 'videos',
            'news': 'news',
            'goggles': 'goggles'
        }
        self.time_range_map = {
            'day': 'pd',
            'week': 'pw',
            'month': 'pm',
            'year': 'py'
        }
        self.safesearch_map = {
            0: 'off',
            1: 'moderate',
            2: 'strict'
        }

    def _get_brave_config(self, category, locale, country):
        return {
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept-Encoding": "gzip, deflate",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1"
            },
            "cookies": {
                "safesearch": self.safesearch_map[0],
                "useLocation": "0",
                "summarizer": "0",
                "country": country.lower(),
                "ui_lang": locale.lower()
            }
        }

    def _parse_results(self, response, category):
        dom = html.fromstring(response.text)
        results = []
        
        if category == 'news':
            for result in dom.xpath('//div[contains(@class, "results")]//div[@data-type="news"]'):
                item = {
                    'title': ' '.join(result.xpath('.//a[contains(@class, "result-header")]//text()')).strip(),
                    'url': result.xpath('.//a[contains(@class, "result-header")]/@href')[0],
                    'content': ' '.join(result.xpath('.//p[contains(@class, "desc")]//text()')).strip(),
                    'thumbnail': result.xpath('.//div[contains(@class, "image-wrapper")]//img/@src')[0]
                }
                results.append(item)
        
        else:  # Default web search
            for result in dom.xpath('//div[contains(@class, "snippet ")]'):
                item = {
                    'url': result.xpath('.//a[contains(@class, "h")]/@href')[0],
                    'title': ' '.join(result.xpath('.//a[contains(@class, "h")]//div[contains(@class, "title")]//text()')).strip(),
                    'content': ' '.join(result.xpath('.//div[contains(@class, "snippet-description")]//text()')).strip()
                }
                results.append(item)
        
        return results

    def search(self, query: str, timeout: int = 10, page: int = 1, 
              category: str = 'search', time_range: str = None, 
              safesearch: int = 0, locale: str = 'en-US', 
              country: str = 'US') -> dict:
        
        try:
            config = self._get_brave_config(category, locale, country)
            params = {
                'q': query,
                'source': 'web',
                'spellcheck': '0'
            }
            
            # Pagination
            if category in ['search', 'goggles'] and page > 1:
                params['offset'] = page - 1
            
            # Time range
            if time_range and category in ['search', 'goggles']:
                params['tf'] = self.time_range_map.get(time_range, '')
            
            # Safesearch
            config['cookies']['safesearch'] = self.safesearch_map.get(safesearch, 'off')
            
            url = f"{self.base_url}{self.category_map[category]}?{urlencode(params)}"
            
            response = requests.get(
                url,
                headers=config['headers'],
                cookies=config['cookies'],
                timeout=timeout
            )
            response.raise_for_status()
            
            return {
                "results": self._parse_results(response, category),
                "metadata": {
                    "page": page,
                    "category": category,
                    "status": "success"
                }
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "metadata": {
                    "status": "failed"
                }
            }
