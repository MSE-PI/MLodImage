from enum import Enum
import requests
import time
import uuid
import threading
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse, FileResponse
from pydantic import BaseModel
from tempfile import NamedTemporaryFile

# Disable warnings
# import warnings
# warnings.filterwarnings("ignore")

api_summary = """
This service is the orchestrator of the MLodImage project. It is responsible for:
- Receiving requests from the client with the audio file
- Call whisper service to generate the lyrics
- Call sentiment-analysis service to analyze the lyrics
- Call music-style service to analyze the style of the music
- Call the image-generation service to generate the cover art

"""

api_description = """
Generate art from lyrics and music style. Returns a JSON object with the following fields:
- image1: the first generated image 
- image2: the second generated image
- image3: the third generated image
"""

# Define the FastAPI application with information
app = FastAPI(
    title="MLodImage Ochestrator API.",
    description=api_description,
    version="0.0.1",
    swagger_ui_parameters={
        "tagsSorter": "alpha",
        "operationsSorter": "method",
    },
    license_info={
        "name": "GNU Affero General Public License v3.0 (GNU AGPLv3)",
        "url": "https://choosealicense.com/licenses/agpl-3.0/",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redirect to docs
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/docs", status_code=301)

class PipelineStatus(str, Enum):
    CREATED = "created"
    WAITING = "waiting"
    RUNNING_WHISPER = "running_whisper"
    RUNNING_SENTIMENT = "running_sentiment"
    RUNNING_MUSIC_STYLE = "running_music_style"
    RUNNING_IMAGE_GENERATION = "running_image_generation"
    FINISHED = "finished"
    FAILED = "failed"

class PipelineInformation(BaseModel):
    id: str
    status: PipelineStatus

class Pipeline(BaseModel):
    informations: PipelineInformation
    audio_path: str = None
    result_path: str = None


piplines: list[Pipeline] = []
audio_supported = ["audio/wav", "audio/mpeg", "audio/x-m4a"]

SERVICE_URL_TEMPLATE = "https://{}-mlodimage.kube.isc.heia-fr.ch"
WHISPER_URL = SERVICE_URL_TEMPLATE.format("whisper")
SENTIMENT_ANALYSIS_URL = SERVICE_URL_TEMPLATE.format("sentiment-analysis")
MUSIC_STYLE_URL = SERVICE_URL_TEMPLATE.format("music-style")
ART_GENERATION_URL = SERVICE_URL_TEMPLATE.format("art-generation")
SERVICE_ROUTE = "/process"

# Get first waiting pipeline
def get_waiting_pipeline():
    for pipeline in piplines:
        if pipeline.informations.status == PipelineStatus.WAITING:
            return pipeline
    return None

# Get pipeline by id
def get_pipeline_by_id(pipeline_id: str):
    for pipeline in piplines:
        if pipeline.informations.id == pipeline_id:
            return pipeline
    return None

# Execute all the waiting pipelines
def run_pipeline():
    while get_waiting_pipeline() is not None:
        pipeline = get_waiting_pipeline()

        # # Call whisper service
        # pipeline.informations.status = PipelineStatus.RUNNING_WHISPER
        # audio_file = open(pipeline.audio_path, "rb")
        # audio_file_bytes = audio_file.read()
        # print("Calling whisper service", WHISPER_URL + SERVICE_ROUTE)
        # response = requests.post(WHISPER_URL + SERVICE_ROUTE, files={"audio": audio_file_bytes})
        # audio_file.close()
        # if response.status_code != 200:
        #     print(response.text)
        #     pipeline.informations.status = PipelineStatus.FAILED
        #     continue
        # lyrics = response.json()

        # # Call sentiment-analysis service
        # pipeline.informations.status = PipelineStatus.RUNNING_SENTIMENT
        # print("Calling sentiment-analysis service", SENTIMENT_ANALYSIS_URL + SERVICE_ROUTE)
        # response = requests.post(SENTIMENT_ANALYSIS_URL + SERVICE_ROUTE, json={"text": lyrics})
        # if response.status_code != 200:
        #     print(response.text)
        #     pipeline.informations.status = PipelineStatus.FAILED
        #     continue
        # sentiment = response.json()

        # # Call music-style service
        # pipeline.informations.status = PipelineStatus.RUNNING_MUSIC_STYLE
        # print("Calling music-style service", MUSIC_STYLE_URL + SERVICE_ROUTE)
        # response = requests.post(MUSIC_STYLE_URL + SERVICE_ROUTE, json={"lyrics": lyrics})
        # if response.status_code != 200:
        #     pipeline.informations.status = PipelineStatus.FAILED
        #     continue
        # music_style = response.json()

        # # Call image-generation service
        # pipeline.informations.status = PipelineStatus.RUNNING_IMAGE_GENERATION
        # print("Calling image-generation service", ART_GENERATION_URL + SERVICE_ROUTE)
        # image_data = {
        #     "lyrics_analysis": {
        #         "language": "en",
        #         "sentiments": sentiment,
        #         "top_words": []
        #     },
        #     "music_style": music_style
        # }
        # print(image_data)
        # response = requests.post(ART_GENERATION_URL + SERVICE_ROUTE, json=image_data)
        # if response.status_code != 200:
        #     pipeline.informations.status = PipelineStatus.FAILED
        #     continue
        # result = response.json()

        # # Save result path
        # pipeline.result_path = result["result_path"]


        # Wait for 30 seconds
        time.sleep(30)

        pipeline.informations.status = PipelineStatus.FINISHED

@app.post("/create", tags=['Pipeline'])
async def create_pipline(audio: UploadFile = File(...)):
    # Generate a random id
    pipeline_id = str(uuid.uuid4())

    # Check if audio file is given
    if audio is None:
        raise HTTPException(status_code=400, detail="No audio file given")
    # Check if audio file is valid
    if audio.content_type not in audio_supported:
        raise HTTPException(status_code=400, detail="Invalid audio file given")
    
    # Save the audio file to the audio folder
    tmp = audio.filename.split('.')
    file_type: str = tmp[len(tmp) - 1]
    audio_path = None
    try:
        with NamedTemporaryFile(suffix="."+file_type, dir="./audios/", delete=False) as f:
            f.write(await audio.read())
            audio_path = f.name
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error while processing audio file")
    
    pipeline = Pipeline(informations=PipelineInformation(id=pipeline_id, status=PipelineStatus.CREATED), audio_path=audio_path)
    piplines.append(pipeline)
    return pipeline.informations

@app.get("/run/{pipeline_id}", tags=['Pipeline'])
async def submit_pipeline(pipeline_id: str):
    print(pipeline_id)
    print(piplines)
    
    pipeline = get_pipeline_by_id(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=400, detail="Invalid pipeline id")
    
    pipeline.informations.status = PipelineStatus.WAITING
    
    # Execute pipeline in a thread
    threading.Thread(target=run_pipeline).start()

    return pipeline.informations

@app.get("/status/{pipeline_id}", tags=['Pipeline'])
async def get_pipeline_status(pipeline_id: str):
    pipline = get_pipeline_by_id(pipeline_id)
    if pipline is None:
        raise HTTPException(status_code=400, detail="Invalid pipeline id")
    return pipline.informations.status

@app.get("/result/{pipeline_id}", tags=['Pipeline'])
async def get_pipeline_result(pipeline_id: str):
    for pipeline in piplines:
        if pipeline.id == pipeline_id:
            return pipeline.result_path
    return None

if __name__ == "__main__":
    # Create test pipeline
    piplines.append(Pipeline(informations=PipelineInformation(id="test", status=PipelineStatus.CREATED), audio_path="./audios/music.wav"))
    pipeline = get_pipeline_by_id("test")

    # Run pipeline
    pipeline.informations.status = PipelineStatus.WAITING
    threading.Thread(target=run_pipeline).start()

    current_status = None
    while pipeline.informations.status != PipelineStatus.FINISHED:
        if pipeline.informations.status != current_status:
            print(pipeline.informations.status)
            current_status = pipeline.informations.status

        if pipeline.informations.status == PipelineStatus.FAILED:
            break

        time.sleep(1)