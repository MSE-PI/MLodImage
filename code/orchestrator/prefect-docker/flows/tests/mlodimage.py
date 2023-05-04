import requests
from prefect import flow, task
from io import BytesIO

# Set up the URLs for each service
BASE_URL_TEMPLATE = "https://{}-mlodimage.kube.isc.heia-fr.ch/"
WHISPER_URL = BASE_URL_TEMPLATE.format("whisper")
SENTIMENT_ANALYSIS_URL = BASE_URL_TEMPLATE.format("sentiment-analysis")
ART_GENERATION_URL = BASE_URL_TEMPLATE.format("art-generation")

# Define the tasks
@task
def call_whisper_api(audio_file):
    """
    Calls the Whisper service API to solve the given audio file
    """
    response = requests.post(WHISPER_URL + "/solve", data=BytesIO(audio_file))
    return response.json()["result"]

@task
def call_sentiment_analysis_api(text, language):
    """
    Calls the Sentiment Analysis service API to analyze the given text
    """
    payload = {"text": text, "language": language}
    response = requests.post(SENTIMENT_ANALYSIS_URL + "/process", json=payload)
    return response.json()

@task
def call_art_generation_api(lyrics_analysis):
    """
    Calls the Art Generation service API to generate art based on the given lyrics analysis
    """
    payload = {"lyrics_analysis": lyrics_analysis}
    response = requests.post(ART_GENERATION_URL + "/process", json=payload)
    return response.json()

@task
def hello_world():
    print("Hello world!")

@flow
def mlodimage_flow():
    hello_world()
    
# Run the flow
mlodimage_flow()