"""
File containing FastAPI routes & start.

To install whisper, run: pip install git+https://github.com/openai/whisper.git

"""

__author__ = "Florian Hofmann"
__date__ = "17.04.2023"

import os
from tempfile import NamedTemporaryFile
import uvicorn

import torch
import whisper

from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from whisper import Whisper

model: Whisper
audio_supported = ["audio/wav", "audio/mpeg", "audio/x-m4a"]
current_path: str = os.getcwd()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan method to load the ML model before the API starts)
    :param app: FastAPI app
    :return:
    """
    global model
    # Check if NVIDIA GPU is available
    torch.cuda.is_available()
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    # Load the ML model
    model = whisper.load_model("base", device=DEVICE)
    print("Model loaded successfully, running on device: " + DEVICE)
    yield  # Yield control to the FastAPI app


# Start API
app = FastAPI(docs_url="/doc", redoc_url=None, lifespan=lifespan)

# Configure CORS
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post('/solve')
async def login(audio: UploadFile = File(...)):
    """
    Route to do the speech recognition on the audio file given in the request.
    """
    # Check if audio file is given
    if audio is None:
        raise HTTPException(status_code=400, detail="No audio file given")
    # Check if audio file is valid
    print(audio.content_type)
    if audio.content_type not in audio_supported:
        raise HTTPException(status_code=400, detail="Invalid audio file given")
    # Save the audio file to the audio folder
    tmp = audio.filename.split('.')
    file_type: str = tmp[len(tmp) - 1]
    try:
        with NamedTemporaryFile(suffix="."+file_type, dir="./audio/", delete=True) as f:
            f.write(await audio.read())
            # Do the speech recognition
            result = model.transcribe(f.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error while processing audio file")

    # Return the result
    return result


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)