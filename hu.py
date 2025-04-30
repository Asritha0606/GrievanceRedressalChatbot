import requests
headers = {"Authorization": f"Bearer {API_TOKEN}"}
API_URL = "https://datasets-server.huggingface.co/info?dataset=ibm/duorc&config=SelfRC"
def query():
    response = requests.get(API_URL, headers=headers)
    return response.json()
data = query()