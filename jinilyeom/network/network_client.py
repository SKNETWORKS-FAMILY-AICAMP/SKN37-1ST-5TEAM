import requests

class HttpClient:
    # TODO: HttpClient 클래스는 싱글톤으로 생성해보는 것을 고려
    def get(self, url, params):
        self.response = requests.get(url, params = params)
        return self.response

    def convert_to_json(self, response):
        return response.json()