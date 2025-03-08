import requests
response = requests.get("https://www.bing.com/search", params={"q": "test", "format": "json"})
print(response.json())
