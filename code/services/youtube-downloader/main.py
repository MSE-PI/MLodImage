import asyncio
import time
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse, Response
from common_code.config import get_settings
from pydantic import Field, BaseModel
from common_code.http_client import HttpClient
from common_code.logger.logger import get_logger
from common_code.service.controller import router as service_router
from common_code.service.service import ServiceService
from common_code.storage.service import StorageService
from common_code.tasks.controller import router as tasks_router
from common_code.tasks.service import TasksService
from common_code.tasks.models import TaskData
from common_code.service.models import Service, FieldDescription
from common_code.service.enums import ServiceStatus, FieldDescriptionType

# Model specific imports
import re
import tempfile
from io import BytesIO
from pytube import YouTube
from fastapi.exceptions import HTTPException


def youtube2mp3(url):
    try:
        # Url input from user
        yt = YouTube(url)
        # Extract audio with 160kbps quality from video
        video_bytes = BytesIO()
        video = yt.streams.filter(only_audio=True).first()

        # Download the file
        video.stream_to_buffer(video_bytes)
        video_bytes.seek(0)
        file = video_bytes

        return file
    except Exception as e:
        print(e)
        return None


settings = get_settings()


class MyService(Service):
    """
    Sentiment analysis service model
    """

    # Any additional fields must be excluded for Pydantic to work
    model: object = Field(exclude=True)

    def __init__(self):
        super().__init__(
            name="Youtube Downloader",
            slug="youtube-downloader",
            url=settings.service_url,
            summary=api_summary,
            description=api_description,
            status=ServiceStatus.AVAILABLE,
            data_in_fields=[
                FieldDescription(name="url", type=[FieldDescriptionType.TEXT_PLAIN]),
            ],
            # !!! temporary to text because audio is not supported yet
            data_out_fields=[
                FieldDescription(name="result", type=[FieldDescriptionType.TEXT_PLAIN]),
            ]
        )

    def process(self, data):
        # Get the text to analyze from storage
        text = data["url"].data
        # bytes to string
        text = text.decode("utf-8")

        # Check if the text is an URL and domain name is youtube.com
        if not re.match(
                "^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube(-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$",
                text
        ):
            raise Exception("Invalid URL, use a youtube.com URL")

        file: BytesIO = youtube2mp3(text)
        if not file:
            raise Exception("Download failed.")
        file_bytes = file.read()
        return {
            "result": TaskData(
                data=file_bytes,
                type=FieldDescriptionType.TEXT_PLAIN
            )
        }


api_summary = """
Download a youtube video to mp3.
"""

api_description = """
Use the given URL to download the video from youtube.com and convert it to mp3.
"""

# Define the FastAPI application with information
app = FastAPI(
    title="Youtube downloader API.",
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

# Include routers from other files
app.include_router(service_router, tags=['Service'])
app.include_router(tasks_router, tags=['Tasks'])

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


service_service: ServiceService | None = None


@app.post("/process", tags=['Process'], response_class=FileResponse)
def handle_process(url: str):
    try:
        result = MyService().process({"url": TaskData(data=url, type=FieldDescriptionType.TEXT_PLAIN)})
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(result["result"].data)
            temp_file.flush()
            return FileResponse(temp_file.name, media_type="audio/mpeg", filename="result.mp3")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@app.on_event("startup")
async def startup_event():
    # Manual instances because startup events doesn't support Dependency Injection
    # https://github.com/tiangolo/fastapi/issues/2057
    # https://github.com/tiangolo/fastapi/issues/425

    # Global variable
    global service_service

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
        for engine_url in settings.engine_url:
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
    #asyncio.ensure_future(announce())


@app.on_event("shutdown")
async def shutdown_event():
    # Global variable
    global service_service
    my_service = MyService()
    for engine_url in settings.engine_url:
        await service_service.graceful_shutdown(my_service, engine_url)
