import asyncio
import json
import time
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
from common_code.service.models import Service
from common_code.service.enums import ServiceStatus
from common_code.common.enums import FieldDescriptionType, ExecutionUnitTagName, ExecutionUnitTagAcronym
from common_code.common.models import FieldDescription, ExecutionUnitTag

# Imports required by the service's model
import os
import zipfile
import torch
from compel import Compel
from diffusers import StableDiffusionPipeline, EulerDiscreteScheduler
from diffusers.pipelines.stable_diffusion.convert_from_ckpt import download_from_original_stable_diffusion_ckpt
from io import BytesIO

# Disable warnings
# import warnings
# warnings.filterwarnings("ignore")

settings = get_settings()
loaded = False
model_ids = ["stabilityai/stable-diffusion-2-base", "prompthero/openjourney", "./music-cover"]
guidance_scale = 5
nb_steps = 50
nb_images_per_model = 1

negative_prompts = "font++, typo++, signature, text++, watermark++, cropped, disfigured, duplicate, error, " \
                   "jpeg artifacts, low quality, lowres, mutated hands, out of frame, worst quality"


def build_pipeline_from_model_id(model_id):
    s = EulerDiscreteScheduler.from_pretrained(model_id, subfolder="scheduler")
    pipe = StableDiffusionPipeline.from_pretrained(model_id, scheduler=s, torch_dtype=torch.float16)
    compel = Compel(tokenizer=pipe.tokenizer, text_encoder=pipe.text_encoder)
    pipe = pipe.to("cuda")
    return pipe, compel

def build_model_from_ckpt(ckpt_path, model_id):
    pipe = download_from_original_stable_diffusion_ckpt(
        checkpoint_path=ckpt_path,
        original_config_file="./v1-inference.yaml"
    )
    pipe.to(torch_dtype=torch.float16)
    pipe.save_pretrained(model_id, safe_serialization=True)


def prompt_builder(lyrics_infos, music_style):
    print("Building prompt...")
    print(music_style["style"])
    print(lyrics_infos["top_words"])

    prompt = f'An album cover in style of {music_style["style"]} without any text and containing the following themes:'
    for i, word in enumerate(lyrics_infos["top_words"]):
        if i == 0:
            prompt += f' {word}++++++'
        elif i == 1:
            prompt += f', {word}++++'
        elif i == 2:
            prompt += f', {word}++'
        else:
            prompt += f', {word}'
    return prompt

def initialize_service():
    """
    Initialize the service
    """
    global loaded, pipes, compels

    # Build model for custom ckpt
    print("Building custom model...")
    model_id = "music-cover"
    cpkt_path = "./music-cover-model.ckpt"
    build_model_from_ckpt(cpkt_path, model_id)
    model_ids.append(f"./{model_id}")

    # Build the pipeline and compel for each model
    print("Building pipelines and compels...")
    pipes = []
    compels = []
    for model_id in model_ids:
        pipe, compel = build_pipeline_from_model_id(model_id)
        pipes.append(pipe)
        compels.append(compel)

    loaded = True

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
                FieldDescription(name="metadata", type=[FieldDescriptionType.APPLICATION_JSON]),
            ],
            tags=[
                ExecutionUnitTag(
                    name=ExecutionUnitTagName.IMAGE_PROCESSING,
                    acronym=ExecutionUnitTagAcronym.IMAGE_PROCESSING
                ),
            ],
        )

    def process(self, data):
        print("Data processing...")
        print(data)

        lyrics_analysis = json.loads(data["lyrics_analysis"].data)
        print(lyrics_analysis)

        music_style = json.loads(data["music_style"].data)
        print(music_style)

        prompt = prompt_builder(lyrics_analysis, music_style)
        print(prompt)

        all_cover_images = []
        for i in range(len(pipes)):
            pipe = pipes[i]
            compel = compels[i]

            prompt_multi = [prompt] * nb_images_per_model
            negative_prompts_multi = [negative_prompts] * nb_images_per_model

            print("Prompt embedding...")
            prompt_embeds = compel(prompt_multi)
            negative_prompts_embeds = compel(negative_prompts_multi)

            print("Image generation...")
            images = pipe(prompt_embeds=prompt_embeds,
                          num_inference_steps=nb_steps,
                          guidance_scale=guidance_scale,
                          negative_prompt_embeds=negative_prompts_embeds,
                          ).images
            all_cover_images += images

        images_bytes = []
        for image in all_cover_images:
            image_bytes = BytesIO()
            image.save(image_bytes, format="PNG")
            images_bytes.append(image_bytes.getvalue())

        return {
            "image1": TaskData(
                data=images_bytes[0],
                type=FieldDescriptionType.IMAGE_PNG,
            ),
            "image2": TaskData(
                data=images_bytes[1],
                type=FieldDescriptionType.IMAGE_PNG,
            ),
            "image3": TaskData(
                data=images_bytes[2],
                type=FieldDescriptionType.IMAGE_PNG,
            ),
            "metadata": TaskData(
                data=json.dumps({
                    "prompt": prompt,
                    "negative_prompts": negative_prompts,
                }),
                type=FieldDescriptionType.APPLICATION_JSON,
            ),
        }


api_summary = """
This service generates art from lyrics and music style.
"""

api_description = """
Generate art from lyrics and music style. Returns a JSON object with the following fields:
- `image1`: the first generated image 
- `image2`: the second generated image
- `image3`: the third generated image
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

    # Initialize the service
    initialize_service()

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


class LyricsAnalysis(BaseModel):
    language: str
    sentiments: dict[str, float]
    top_words: list[str]


class MusicStyle(BaseModel):
    style: str


class Data(BaseModel):
    lyrics_analysis: LyricsAnalysis
    music_style: MusicStyle


@app.post("/process", tags=['Process'])
async def handle_process(data: Data):
    lyrics_analysis = data.lyrics_analysis
    music_style = data.music_style

    lyrics_analysis = json.dumps(lyrics_analysis.dict())
    music_style = json.dumps(music_style.dict())

    print("Calling art generation service")
    result = MyService().process(
        {
            "lyrics_analysis":
                TaskData(data=lyrics_analysis, type=FieldDescriptionType.APPLICATION_JSON),
            "music_style":
                TaskData(data=music_style, type=FieldDescriptionType.APPLICATION_JSON)
        })

    images = []
    images.append(result["image1"].data)
    images.append(result["image2"].data)
    images.append(result["image3"].data)

    print("Save images as temp files")
    image_dir = "images"
    os.makedirs(image_dir, exist_ok=True)
    for i, image in enumerate(images):
        # image is bytes
        image_path = os.path.join(image_dir, f"image{i}.png")
        print("image_path", image_path)
        with open(image_path, "wb") as f:
            f.write(image)

    # Build an archive containing the images
    print("Building archive")
    archive = BytesIO()
    with zipfile.ZipFile(archive, 'w') as zip_file:
        print("Add images to the archive")
        for root, dirs, files in os.walk(image_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path)

    # Save the archive on disk
    print("Save archive on disk")
    archive_path = "images.zip"
    with open(archive_path, "wb") as f:
        f.write(archive.getvalue())

    print("Archive", type(archive.getvalue()))
    print("Archive path", archive_path)

    return FileResponse(archive_path, media_type="application/zip", filename="images.zip",
                        headers=json.loads(result["metadata"].data))


@app.post("/test", tags=['Test'])
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
