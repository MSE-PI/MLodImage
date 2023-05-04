from enum import Enum
import uuid
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse, FileResponse
from pydantic import BaseModel

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
    PENDING = "pending"
    RUNNING_WHISPER = "running_whisper"
    RUNNING_SENTIMENT = "running_sentiment"
    RUNNING_MUSIC_STYLE = "running_music_style"
    RUNNING_IMAGE_GENERATION = "running_image_generation"
    FINISHED = "finished"

class Pipeline(BaseModel):
    id: str
    status: PipelineStatus
    result_path: str = None

piplines = []

@app.get("/create", tags=['Pipeline'])
async def create_pipline():
    # Generate a random id
    pipeline_id = str(uuid.uuid4())
    pipeline = Pipeline(id=pipeline_id, status=PipelineStatus.PENDING)
    return pipeline

# Run pipeline
@app.post("/run/{pipeline_id}", tags=['Pipeline'])
async def run_pipeline(pipeline_id: str, audio: UploadFile = File(...)):
    for pipeline in piplines:
        if pipeline.id == pipeline_id:
            pipeline.status = PipelineStatus.FINISHED
            break
    return pipeline

@app.get("/status/{pipeline_id}", tags=['Pipeline'])
async def get_pipeline_status(pipeline_id: str):
    for pipeline in piplines:
        if pipeline.id == pipeline_id:
            return pipeline.status
    return None

@app.get("/result/{pipeline_id}", tags=['Pipeline'])
async def get_pipeline_result(pipeline_id: str):
    for pipeline in piplines:
        if pipeline.id == pipeline_id:
            return pipeline.result_path
    return None