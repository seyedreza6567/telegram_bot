import requests

def test_connection():
    url = "https://api.toobit.com"
    try:
        response = requests.get(url, timeout=10)
        return response.status_code
    except Exception as e:
        return str(e)
