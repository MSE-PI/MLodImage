import requests
from prefect import flow, task

@task
def call_api(url):
    response = requests.get(url)
    print(response.status_code)
    return response.json()

@flow(persist_result=True)
def api_flow(url):
    fact_json = call_api(url)
    print(fact_json["fact"])
    return fact_json["fact"]
