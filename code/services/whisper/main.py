"""
File containing FastAPI routes & start.

To install whisper, run: pip install git+https://github.com/openai/whisper.git

"""

# Common import
import asyncio
import json
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from common_code.config import get_settings
from pydantic import Field
from common_code.http_client import HttpClient
from common_code.logger.logger import get_logger
from common_code.service.controller import router as service_router
from common_code.service.service import ServiceService
from common_code.storage.service import StorageService
from common_code.tasks.controller import router as tasks_router
from common_code.tasks.service import TasksService
from common_code.tasks.models import TaskData
from common_code.service.models import Service
from common_code.service.enums import ServiceStatus
from common_code.common.enums import FieldDescriptionType, ExecutionUnitTagName, ExecutionUnitTagAcronym
from common_code.common.models import FieldDescription, ExecutionUnitTag

# service specific imports
import os
import torch
import whisper
from tempfile import NamedTemporaryFile
from fastapi import UploadFile, File, HTTPException
from whisper import Whisper

settings = get_settings()

model: Whisper
audio_supported = ["audio/mpeg", "audio/ogg"]
current_path: str = os.getcwd()


class MyService(Service):
    """
    Whisper service model
    """

    # Any additional fields must be excluded for Pydantic to work
    model: object = Field(exclude=True)

    def __init__(self):
        super().__init__(
            name="Whisper",
            slug="Whisper",
            url=settings.service_url,
            summary=api_summary,
            description=api_description,
            status=ServiceStatus.AVAILABLE,
            data_in_fields=[
                FieldDescription(name="audio", type=[FieldDescriptionType.AUDIO_MP3, FieldDescriptionType.AUDIO_OGG]),
            ],
            data_out_fields=[
                FieldDescription(name="result", type=[FieldDescriptionType.APPLICATION_JSON]),
            ],
            tags=[
                ExecutionUnitTag(
                    name=ExecutionUnitTagName.SPEECH_RECOGNITION,
                    acronym=ExecutionUnitTagAcronym.SPEECH_RECOGNITIONm
                ),
            ],
        )

        # load the model :
        torch.cuda.is_available()  # Check if NVIDIA GPU is available
        DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        # Load the ML model
        self.model = whisper.load_model("base", device=DEVICE)
        print("Model loaded successfully, running on device: " + DEVICE)

    def process(self, data):
        # Get
        audio = data["audio"].data
        # Save the audio file to the audio folder
        try:
            with NamedTemporaryFile(dir="./audio/", delete=True) as f:
                f.write(audio)
                # Do the speech recognition
                result = my_service.model.transcribe(f.name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        return {
            "result": TaskData(
                data=json.dumps(result),
                type=FieldDescriptionType.APPLICATION_JSON
            )
        }


api_summary = """
Transcribe any audio file to text
"""

api_description = """
Transcribe any audio file to text. Returns a JSON object with the following fields:
- `transcription`: the text extracted from the audio file
"""

# Define the FastAPI application with information
app = FastAPI(
    title="Whisper API.",
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

# Include routers from other files
app.include_router(service_router, tags=['Service'])
app.include_router(tasks_router, tags=['Tasks'])


# Redirect to docs
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/docs", status_code=301)


service_service: ServiceService | None = None
my_service: MyService | None = None


@app.on_event("startup")
async def startup_event():
    # Manual instances because startup events doesn't support Dependency Injection
    # https://github.com/tiangolo/fastapi/issues/2057
    # https://github.com/tiangolo/fastapi/issues/425

    # Global variable
    global service_service, my_service

    logger = get_logger(settings)
    http_client = HttpClient()
    storage_service = StorageService(logger)
    my_service = MyService()
    tasks_service = TasksService(logger, settings, http_client, storage_service)
    service_service = ServiceService(logger, settings, http_client, tasks_service)

    tasks_service.set_service(my_service)

    # Start the tasks service
    tasks_service.start()

    async def announce():
        retries = settings.engine_announce_retries
        for engine_url in settings.engine_urls:
            announced = False
            while not announced and retries > 0:
                announced = await service_service.announce_service(my_service, engine_url)
                retries -= 1
                if not announced:
                    time.sleep(settings.engine_announce_retry_delay)
                    if retries == 0:
                        logger.warning(f"Aborting service announcement after "
                                       f"{settings.engine_announce_retries} retries")

    # Announce the service to its engine
    asyncio.ensure_future(announce())


@app.on_event("shutdown")
async def shutdown_event():
    # Global variable
    global service_service
    my_service = MyService()
    for engine_url in settings.engine_urls:
        await service_service.graceful_shutdown(my_service, engine_url)


@app.post('/process', tags=['Process'])
async def process(audio: UploadFile = File(...)):
    """
    Route to do the speech recognition on the audio file given in the request
    """
    # Check if audio file is given
    if audio is None:
        raise HTTPException(status_code=400, detail="No audio file given")
    # Check if audio file is valid
    if audio.content_type not in audio_supported:
        raise HTTPException(status_code=400, detail="Invalid audio file given")
    # Get audio file type
    if audio.content_type == "audio/mpeg":
        AUDIO_TYPE = FieldDescriptionType.AUDIO_MP3
    else:
        AUDIO_TYPE = FieldDescriptionType.AUDIO_OGG
    # convert audio to bytes
    audio_bytes = await audio.read()
    # call service to process audio
    result = MyService().process({"audio": TaskData(data=audio_bytes, type=AUDIO_TYPE)})
    # Return the result
    data = json.loads(result["result"].data)
    return data
