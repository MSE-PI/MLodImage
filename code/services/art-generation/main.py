import asyncio
import json
import os
import tempfile
import time
import zipfile
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse, FileResponse
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

# Imports required by the service's model
from io import BytesIO
import torch
from compel import Compel
from diffusers import StableDiffusionPipeline, EulerDiscreteScheduler, AutoencoderKL, UNet2DConditionModel, LMSDiscreteScheduler

# Disable warnings
# import warnings
# warnings.filterwarnings("ignore")

settings = get_settings()
model_id = "stabilityai/stable-diffusion-2-base"
guidance_scale = 5
nb_steps = 80

scheduler = EulerDiscreteScheduler.from_pretrained(model_id, subfolder="scheduler")
pipe = StableDiffusionPipeline.from_pretrained(model_id, scheduler=scheduler).to("cuda")
compel = Compel(tokenizer=pipe.tokenizer, text_encoder=pipe.text_encoder)

negative_prompts = "font, typo, signature, text, watermark, cropped, disfigured, duplicate, error, jpeg artifacts, low quality, lowres, mutated hands, out of frame, worst quality"

def prompt_builder(lyrics_infos, music_style):
    print("Building prompt...")
    print(music_style["style"])
    print(lyrics_infos["top_words"])

    prompt = f'{music_style["style"]} album cover with lyrics about'
    for word in lyrics_infos["top_words"]:
        prompt += f' {word}'
    return prompt


class MyService(Service):
    """
    Art generation service model
    """

    # Any additional fields must be excluded for Pydantic to work
    model: object = Field(exclude=True)

    def __init__(self):
        super().__init__(
            name="Art Generation",
            slug="art_generation",
            url=settings.service_url,
            summary=api_summary,
            description=api_description,
            status=ServiceStatus.AVAILABLE,
            data_in_fields=[
                FieldDescription(name="lyrics_analysis", type=[FieldDescriptionType.APPLICATION_JSON]),
                FieldDescription(name="music_style", type=[FieldDescriptionType.APPLICATION_JSON]),
            ],
            data_out_fields=[
                FieldDescription(name="image1", type=[FieldDescriptionType.IMAGE_PNG]),
                FieldDescription(name="image2", type=[FieldDescriptionType.IMAGE_PNG]),
                FieldDescription(name="image3", type=[FieldDescriptionType.IMAGE_PNG]),
            ]
        )

    def process(self, data):
        # Get the data from the input fields as bytes
        lyrics_analysis = data["lyrics_analysis"].data
        music_style = data["music_style"].data
        settings = data["settings"].data

        # transform bytes to json
        lyrics_analysis = json.loads(lyrics_analysis)
        music_style = json.loads(music_style)
        settings = json.loads(settings)
        nb_images = settings["nb_images"]

        prompt = prompt_builder(lyrics_analysis, music_style)

        prompt_multi = [prompt] * nb_images
        negative_prompts_multi = [negative_prompts] * nb_images

        prompt_embeds = compel(prompt_multi)
        negative_prompts_embeds = compel(negative_prompts_multi)

        images = pipe(prompt_embeds=prompt_embeds,
                    num_inference_steps=nb_steps,
                    guidance_scale=guidance_scale,
                    negative_prompt_embeds=negative_prompts_embeds,
                    ).images
        

        results = []
        for image in images:
            result = BytesIO()
            image.save(result, format="PNG")
            result.seek(0)
            results.append(result.read())

        # NOTE that the result must be a dictionary with the keys being the field names set in the data_out_fields
        return {
            "result": {
                "image1": TaskData(
                    data=results[0],
                    type=FieldDescriptionType.IMAGE_PNG,
                ),
                "image2": TaskData(
                    data=results[1],
                    type=FieldDescriptionType.IMAGE_PNG,
                ),
                "image3": TaskData(
                    data=results[2],
                    type=FieldDescriptionType.IMAGE_PNG,
                ),
            }
        }

api_summary = """
This service generates art from lyrics and music style.
"""

api_description = """
Generate art from lyrics and music style and return a PNG image.
"""

# Define the FastAPI application with information
app = FastAPI(
    title="Art Generation API.",
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
        # TODO: enhance this to allow multiple engines to be used
        announced = False

        retries = settings.engine_announce_retries
        while not announced and retries > 0:
            announced = await service_service.announce_service(my_service)
            retries -= 1
            if not announced:
                time.sleep(settings.engine_announce_retry_delay)
                if retries == 0:
                    logger.warning(f"Aborting service announcement after {settings.engine_announce_retries} retries")

    # Announce the service to its engine
    asyncio.ensure_future(announce())


@app.on_event("shutdown")
async def shutdown_event():
    # Global variable
    global service_service
    my_service = MyService()
    await service_service.graceful_shutdown(my_service)

class LyricsAnalysis(BaseModel):
    language: str
    sentiments: dict[str, float]
    top_words: list[str]

class MusicStyle(BaseModel):
    style: str

# Custom route to bypass the engine
@app.post("/process")
async def test(lyrics_analysis: LyricsAnalysis, music_style: MusicStyle, nb_images: int = 3):
    s = EulerDiscreteScheduler.from_pretrained(model_id, subfolder="scheduler")
    p = StableDiffusionPipeline.from_pretrained(model_id, scheduler=s).to("cuda")
    c = Compel(tokenizer=p.tokenizer, text_encoder=p.text_encoder)

    print("Data processing...")
    # decode the json
    lyrics_analysis = {
        "language": lyrics_analysis.language,
        "sentiments": lyrics_analysis.sentiments,
        "top_words": lyrics_analysis.top_words
    }

    music_style = {
        "style": music_style.style
    }

    prompt = prompt_builder(lyrics_analysis, music_style)
    print(prompt)
    
    prompt_multi = [prompt] * nb_images
    negative_prompts_multi = [negative_prompts] * nb_images

    print("Prompt embedding...")
    prompt_embeds = c(prompt_multi)
    negative_prompts_embeds = c(negative_prompts_multi)

    print("Image generation...")
    images = p(prompt_embeds=prompt_embeds,
                num_inference_steps=nb_steps,
                guidance_scale=guidance_scale,
                negative_prompt_embeds=negative_prompts_embeds,
                ).images

    # Write the images to a temporary directory
    with tempfile.TemporaryDirectory() as tmpdirname:
        for i, image in enumerate(images):
            image.save(os.path.join(tmpdirname, f"image_{i}.png"))

        # Build an archive containing the images
        archive = BytesIO()
        with zipfile.ZipFile(archive, 'w') as zip_file:
            for root, dirs, files in os.walk(tmpdirname):
                for file in files:
                    file_path = os.path.join(root, file)
                    zip_file.write(file_path)

    return FileResponse(archive, media_type="application/zip", filename="images.zip")
    

@app.post("/test")
async def test(prompt: str, negative_prompts: str):
    s = EulerDiscreteScheduler.from_pretrained(model_id, subfolder="scheduler")
    p = StableDiffusionPipeline.from_pretrained(model_id, scheduler=s).to("cuda")
    c = Compel(tokenizer=p.tokenizer, text_encoder=p.text_encoder)

    print("Prompt embedding...")
    prompt_embeds = c(prompt)
    negative_prompts_embeds = c(negative_prompts)

    print("Image generation...")
    images = p(prompt_embeds=prompt_embeds,
                num_inference_steps=nb_steps,
                guidance_scale=guidance_scale,
                negative_prompt_embeds=negative_prompts_embeds,
                ).images
    
    print("Image processing...")
    result = BytesIO()
    images[0].save(result, format="PNG")
    result.seek(0)

    return StreamingResponse(result, media_type="image/png")