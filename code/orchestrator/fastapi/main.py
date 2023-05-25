from enum import Enum
import os
from typing import Optional
import requests
import time
import uuid
import threading
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel
from tempfile import NamedTemporaryFile
import zipfile
import io
import asyncio

api_description = """
This service is the orchestrator of the MLodImage project. It is responsible for:
- Receiving requests from the client with the audio file or a YouTube URL
- Call youtube-downloader service to download the audio file
- Call whisper service to generate the lyrics
- Call sentiment-analysis service to analyze the lyrics
- Call music-style service to analyze the style of the music
- Call the image-generation service to generate the cover art
"""

api_summary = """
Orchestrator API for the MLodImage project.
"""

# Define the FastAPI application with information
app = FastAPI(
    title="MLodImage Orchestrator API.",
    description=api_description,
    summary=api_summary,
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


class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, execution_id: str):
        await websocket.accept()
        print(f"websocket {execution_id} accepted")
        self.active_connections[execution_id] = websocket

    async def disconnect(self, execution_id: str):
        print(f"websocket {execution_id} disconnected")
        await self.active_connections[execution_id].close()
        del self.active_connections[execution_id]

    async def send_json(self, message: dict, execution_id: str):
        await self.active_connections[execution_id].send_json(message)

    async def send_bytes(self, message: bytes, execution_id: str):
        await self.active_connections[execution_id].send_bytes(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)


manager = ConnectionManager()


class PipelineStatus(str, Enum):
    CREATED = "created"
    WAITING = "waiting"
    RUNNING_YOUTUBE_DOWNLOADER = "running_youtube_downloader"
    RUNNING_WHISPER = "running_whisper"
    RUNNING_SENTIMENT = "running_sentiment"
    RUNNING_MUSIC_STYLE = "running_music_style"
    RUNNING_IMAGE_GENERATION = "running_image_generation"
    FINISHED = "finished"
    FAILED = "failed"
    RESULT_READY = "result_ready"


class PipelineInformation(BaseModel):
    id: str
    status: PipelineStatus
    results: dict = {
        "youtube_downloader": None,
        "whisper": None,
        "sentiment_analysis": None,
        "music_style": None,
    }


class Pipeline(BaseModel):
    informations: PipelineInformation
    audio_path: str = None
    audio_type: str = None
    result_path: str = None
    url: str = None


pipelines: list[Pipeline] = []
audio_supported = ["audio/mpeg", "audio/ogg"]

SERVICE_URL_TEMPLATE = "https://{}-mlodimage.kube.isc.heia-fr.ch"
YOUTUBE_DOWNLOADER_URL = SERVICE_URL_TEMPLATE.format("youtube-downloader")
WHISPER_URL = SERVICE_URL_TEMPLATE.format("whisper")
SENTIMENT_ANALYSIS_URL = SERVICE_URL_TEMPLATE.format("sentiment-analysis")
MUSIC_STYLE_URL = SERVICE_URL_TEMPLATE.format("genre-detection")
ART_GENERATION_URL = SERVICE_URL_TEMPLATE.format("art-generation")
SERVICE_ROUTE = "/process"


async def save_audio(audio: io.BytesIO, file_type: str):
    # Save the audio file to the audios folder
    try:
        with NamedTemporaryFile(suffix="." + file_type, dir="./audios/", delete=False) as f:
            f.write(audio.read())
            return f.name
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error while processing audio file")


def delete_pipeline(pipeline_id: str):
    for pipeline in pipelines:
        if pipeline.informations.id == pipeline_id:
            # Delete audio file
            if pipeline.audio_path:
                os.remove(pipeline.audio_path)
            # Delete result file
            if pipeline.result_path:
                os.remove(pipeline.result_path)
            pipelines.remove(pipeline)
            return
    return None


def get_waiting_pipeline():
    for pipeline in pipelines:
        if pipeline.informations.status == PipelineStatus.WAITING:
            return pipeline
    return None


def delete_finished_pipelines():
    for pipeline in pipelines:
        if pipeline.informations.status == PipelineStatus.FINISHED:
            delete_pipeline(pipeline.informations.id)


def get_pipeline_by_id(pipeline_id: str):
    print("get_pipeline_by_id", pipeline_id)
    for pipeline in pipelines:
        print(pipeline.informations.id)
        if pipeline.informations.id == pipeline_id:
            return pipeline
    return None


def start_pipeline_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_pipeline())


# Update pipeline status and send it to the client
async def update_pipeline_status(pipeline: Pipeline, status: PipelineStatus, result_dict_key: str, result_value):
    pipeline.informations.results[result_dict_key] = result_value
    pipeline.informations.status = status
    # find the client websocket with the same id
    for connection_id, _ in manager.active_connections.items():
        if connection_id == pipeline.informations.id:
            await manager.send_json(pipeline.informations.dict(), connection_id)
            return


def isResponseOK(response: requests.Response):
    if response.status_code != 200:
        print("Error while calling service", response.status_code, response.content)
        return False
    return True


# Execute all the waiting pipelines
async def run_pipeline():
    while get_waiting_pipeline() is not None:
        pipeline = get_waiting_pipeline()

        if pipeline.audio_path is None:
            # Call youtube-downloader service
            await update_pipeline_status(pipeline, PipelineStatus.RUNNING_YOUTUBE_DOWNLOADER, "youtube_downloader",
                                         "Downloading audio")
            print("Calling youtube-downloader service", YOUTUBE_DOWNLOADER_URL + SERVICE_ROUTE)
            response = requests.post(YOUTUBE_DOWNLOADER_URL + SERVICE_ROUTE, params={"url": pipeline.url})
            if not isResponseOK(response):
                await update_pipeline_status(pipeline, PipelineStatus.FAILED, "youtube_downloader",
                                             "Error while downloading audio")
                continue
            # Transform response.content to a BinaryIO
            audio = io.BytesIO(response.content)
            pipeline.audio_path = await save_audio(audio, "mp3")

        # Call whisper service
        await update_pipeline_status(pipeline, PipelineStatus.RUNNING_WHISPER, "youtube_downloader",
                                     pipeline.audio_path)
        audio_file = open(pipeline.audio_path, "rb")
        audio_file_bytes = audio_file.read()
        audio_type = pipeline.audio_type if pipeline.audio_type else "audio/wav"
        print("Calling whisper service", WHISPER_URL + SERVICE_ROUTE)
        response = requests.post(WHISPER_URL + SERVICE_ROUTE,
                                 files={"audio": (pipeline.audio_path, audio_file_bytes, audio_type)})
        audio_file.close()
        if not isResponseOK(response):
            await update_pipeline_status(pipeline, PipelineStatus.FAILED, "whisper", "Error while extracting lyrics")
            continue
        lyrics = response.json()
        lyrics = lyrics["text"]

        # Call sentiment-analysis service
        await update_pipeline_status(pipeline, PipelineStatus.RUNNING_SENTIMENT, "whisper", lyrics)
        print("Calling sentiment-analysis service", SENTIMENT_ANALYSIS_URL + SERVICE_ROUTE)
        response = requests.post(SENTIMENT_ANALYSIS_URL + SERVICE_ROUTE, json={"text": lyrics})
        if not isResponseOK(response):
            await update_pipeline_status(pipeline, PipelineStatus.FAILED, "sentiment_analysis",
                                         "Error while analyzing lyrics")
            continue
        sentiment_analysis = response.json()

        # Call music-style service
        await update_pipeline_status(pipeline, PipelineStatus.RUNNING_MUSIC_STYLE, "sentiment_analysis",
                                     sentiment_analysis)
        print("Calling music-style service", MUSIC_STYLE_URL + SERVICE_ROUTE)
        response = requests.post(MUSIC_STYLE_URL + SERVICE_ROUTE,
                                 files={"audio": (pipeline.audio_path, audio_file_bytes, audio_type)})
        if not isResponseOK(response):
            await update_pipeline_status(pipeline, PipelineStatus.FAILED, "music_style", "Error while analyzing music")
            continue
        music_style = response.json()

        # Call image-generation service
        await update_pipeline_status(pipeline, PipelineStatus.RUNNING_IMAGE_GENERATION, "music_style", music_style)
        print("Calling image-generation service", ART_GENERATION_URL + SERVICE_ROUTE)
        image_data = {
            "lyrics_analysis": sentiment_analysis,
            "music_style": {
                "style": music_style["genre_top"],
            }
        }
        response = requests.post(ART_GENERATION_URL + SERVICE_ROUTE, json=image_data)
        if not isResponseOK(response):
            await update_pipeline_status(pipeline, PipelineStatus.FAILED, "image_generation",
                                         "Error while generating images")
            continue

        print("Creating zip file with generated images")
        zip_file_content = response.content

        # Save the zip file to disk
        zf = zipfile.ZipFile(io.BytesIO(zip_file_content))

        # Write zip file to disk
        archive_path = f"results/images_{pipeline.informations.id}.zip"
        with zipfile.ZipFile(archive_path, "w") as f:
            for file in zf.namelist():
                f.writestr(file, zf.read(file))

        pipeline.result_path = archive_path
        await update_pipeline_status(pipeline, PipelineStatus.RESULT_READY, "image_generation", "Images generated")


@app.get("/reload", tags=['Pipeline'])
async def reload():
    """
    Reload the pipeline list
    """
    threading.Thread(target=run_pipeline).start()
    return {"message": "Reloaded"}


@app.post("/create", tags=['Pipeline'])
async def create_pipeline(audio: Optional[UploadFile] = File(None), url: Optional[str] = Form(None)):
    """
    Create a new pipeline
    """

    # Generate a random id and create a new pipeline
    pipeline = Pipeline(informations=PipelineInformation(status=PipelineStatus.CREATED, id=str(uuid.uuid4())))

    # Check if audio file or url is given
    if audio is None and url is None:
        raise HTTPException(status_code=400, detail="No audio file or url given")

    # If url is given, download the file to a temporary directory
    if url is not None:
        pipeline.url = url
    else:
        # Check if audio file is valid
        if audio.content_type not in audio_supported:
            raise HTTPException(status_code=400, detail="Invalid audio file given")

        # Save the audio file to the audio folder
        pipeline.audio_type = audio.content_type
        tmp = audio.filename.split('.')
        file_type = tmp[len(tmp) - 1]
        pipeline.audio_path = await save_audio(audio.file, file_type)

    pipelines.append(pipeline)
    return pipeline.informations


@app.get("/run/{pipeline_id}", tags=['Pipeline'])
async def submit_pipeline(pipeline_id: str):
    """
    Submits the pipeline to the pipeline manager
    """
    delete_finished_pipelines()

    pipeline = get_pipeline_by_id(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=400, detail="Invalid pipeline id")
    if pipeline.informations.status != PipelineStatus.CREATED:
        raise HTTPException(status_code=400, detail="The pipeline was already submitted")

    pipeline.informations.status = PipelineStatus.WAITING

    threading.Thread(target=start_pipeline_thread).start()

    return PipelineInformation(id=pipeline_id, status=PipelineStatus.WAITING)


@app.get("/status/{pipeline_id}", tags=['Pipeline'])
async def get_pipeline_status(pipeline_id: str):
    """
    Returns the status of the pipeline
    """
    pipeline = get_pipeline_by_id(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=400, detail="Invalid pipeline id")
    return pipeline.informations.status


@app.get("/result/{pipeline_id}", tags=['Pipeline'])
async def get_pipeline_result(pipeline_id: str):
    """
    Returns the result of the pipeline as a zip file
    """
    # Get pipeline
    pipeline = get_pipeline_by_id(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=400, detail="Invalid pipeline id")
    # Check if pipeline is finished
    if pipeline.informations.status != PipelineStatus.RESULT_READY:
        raise HTTPException(status_code=400, detail="Pipeline is not finished yet")

    pipeline.informations.status = PipelineStatus.FINISHED

    return FileResponse(pipeline.result_path, media_type="application/zip", filename=pipeline.result_path)


@app.get("/pipelines", tags=['Pipeline'])
async def get_pipelines():
    """
    Returns a list of all pipelines
    """
    return [pipeline.informations for pipeline in pipelines]


@app.get("/reset", tags=['Pipeline'])
async def reset_pipelines():
    """
    Delete all pipelines and removes all files in the audios and results folder
    """
    pipelines.clear()
    # Remove all files in the audios folder
    for file in os.listdir("./audios/"):
        if file != ".gitkeep":
            os.remove("./audios/" + file)

    # Remove all files in the results folder
    for file in os.listdir("./results/"):
        if file != ".gitkeep":
            os.remove("./results/" + file)


@app.websocket("/ws/{pipeline_id}")
async def websocket_endpoint(websocket: WebSocket, pipeline_id: str):
    """
    Websocket endpoint for the pipeline status
    """
    pipeline = get_pipeline_by_id(pipeline_id)
    if pipeline is None:
        # Refuse connection
        await manager.connect(websocket, pipeline_id)
        await websocket.send_json({"error": "Invalid pipeline id"})
        await websocket.close()
        return

    await manager.connect(websocket, pipeline.informations.id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(pipeline.informations.id)


if __name__ == "__main__":
    # Create test pipeline
    pipelines.append(Pipeline(informations=PipelineInformation(id="test", status=PipelineStatus.CREATED),
                              audio_path="./audios/music.wav"))
    test_pipeline = get_pipeline_by_id("test")

    # Run pipeline
    test_pipeline.informations.status = PipelineStatus.WAITING
    threading.Thread(target=run_pipeline).start()

    # Wait for pipeline to finish
    current_status = None
    while test_pipeline.informations.status != PipelineStatus.RESULT_READY:
        if test_pipeline.informations.status != current_status:
            print(test_pipeline.informations.status)
            current_status = test_pipeline.informations.status

        if test_pipeline.informations.status == PipelineStatus.FAILED:
            break

        time.sleep(1)
