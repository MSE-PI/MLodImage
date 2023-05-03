"""
Service responsible for detecting the musical genre of a song.
"""

__author__ = "Benjamin Pasquier"
__date__ = "03.05.2023"

# Common import
import asyncio
import json
import time
from fastapi import FastAPI, HTTPException
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
from common_code.service.models import Service, FieldDescription
from common_code.service.enums import ServiceStatus, FieldDescriptionType

# service specific imports
import torchaudio
import torch
import os
import numpy as np

# audio configuration TODO: move to config file
AUDIO_DURATION = 3000 # equals 3 seconds
SAMPLE_RATE = 44100
N_CHANNELS = 1

settings = get_settings()

class AudioUtil():
    """
    Utility class for audio processing.
    """
    @staticmethod
    def open(audio_file):
        """
        Open an audio file and return the signal and the sample rate.
        :param audio_file: a file-like object or a path to an audio file
        :type audio_file: Union[str, pathlib.Path, FileLike]
        :return: the signal and the sample rate
        """
        signal, sample_rate = torchaudio.load(audio_file)
        return (signal, sample_rate)
    
    @staticmethod
    def rechannel(audio, new_channel):
        """
        Convert a given audio to the specified number of channels.
        :param audio: the audio, composed of the signal and the sample rate
        :type audio: Tuple[torch.Tensor, int]
        :param new_channel: the target number of channels
        :type new_channel: int
        :return: the audio with the target number of channels
        :rtype: Tuple[torch.Tensor, int]
        """
        signal, sample_rate = audio

        if (signal.shape[0] == new_channel):
            # nothing to do as the signal already has the target number of channels
            return audio
        if (new_channel == 1):
            # convert to mono by selecting only the first channel
            signal = signal[:1, :]
        else:
            # convert to stereo by duplicating the first channel
            signal = torch.cat([signal, signal])
        return (signal, sample_rate)
    
    @staticmethod
    def resample(audio, new_sample_rate):
        """
        Change the sample rate of the audio signal.
        :param audio: the audio, composed of the signal and the sample rate
        :type audio: Tuple[torch.Tensor, int]
        :param new_sample_rate: the target sample rate
        :type new_sample_rate: int
        :return: the audio with the target sample rate
        :rtype: Tuple[torch.Tensor, int]
        """
        signal, sample_rate = audio
        if (sample_rate == new_sample_rate):
            # nothing to do
            return audio
        resample = torchaudio.transforms.Resample(sample_rate, new_sample_rate)
        signal = resample(signal)
        return (signal, new_sample_rate)
    
    @staticmethod
    def pad_truncate(audio, length):
        """
        Pad or truncate an audio signal to a fixed length (in ms).
        :param audio: the audio, composed of the signal and the sample rate
        :type audio: Tuple[torch.Tensor, int]
        :param length: the target length in ms
        :type length: int
        :return: the audio with the target length
        :rtype: Tuple[torch.Tensor, int]
        """
        signal, sample_rate = audio
        max_length = sample_rate//1000 * length

        if (signal.shape[1] > max_length):
            signal = signal[:, :max_length]
        elif (signal.shape[1] < max_length):
            padding = max_length - signal.shape[1]
            signal = F.pad(signal, (0, padding))
        return (signal, sample_rate)
    
    @staticmethod
    def mel_spectrogram(audio, n_mels=64, n_fft=1024, hop_length=None):
        """
        Create the mel spectogram for the given audio signal.
        :param audio: the audio, composed of the signal and the sample rate
        :type audio: Tuple[torch.Tensor, int]
        :param n_mels: the number of mel filterbanks
        :type n_mels: int
        :param n_fft: the size of the FFT
        :type n_fft: int
        :param hop_length: the length of hop between STFT windows
        :type hop_length: int
        :return: the mel spectogram
        :rtype: torch.Tensor
        """
        signal, sample_rate = audio
        
        mel_spectrogram = torchaudio.transforms.MelSpectrogram(
            sample_rate,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels
        )(signal)

        # convert to decibels
        mel_spectrogram = torchaudio.transforms.AmplitudeToDB()(mel_spectrogram)

        return mel_spectrogram

class MyService(Service):
    """
    Musical genre detection service model.
    """

    # Any additional fields must be excluded for Pydantic to work
    model: object = Field(exclude=True)

    def __init__(self):
        super().__init__(
            name="Musical Genre Detection",
            slug="muscial_genre_detection",
            url=settings.service_url,
            summary=api_summary,
            description=api_description,
            status=ServiceStatus.AVAILABLE,
            data_in_fields=[
                FieldDescription(name="text", type=[FieldDescriptionType.TEXT_PLAIN]),
            ],
            data_out_fields=[
                FieldDescription(name="result", type=[FieldDescriptionType.APPLICATION_JSON]),
            ]
        )

        # load json file containing the mapping between the genre and the index
        with open('id_to_label') as f:
            self.mapping = json.load(f)

        # load the model
        torch.cuda.is_available()  # Check if NVIDIA GPU is available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # TODO : download the model from Minio
        self.model = torch.load('model.h5').to(self.device)
        print("Model loaded successfully, running on device: " + self.device)

    def process(self, data):
        # load and preprocess the audio file
        audio = AudioUtil.open(data)
        audio = AudioUtil.rechannel(audio, N_CHANNELS)
        audio = AudioUtil.resample(audio, SAMPLE_RATE)
        audio = AudioUtil.pad_truncate(audio, AUDIO_DURATION)
        mel_spectrogram = AudioUtil.mel_spectrogram(audio)

        # inference
        # inference
        inputs = mel_spectrogram.unsqueeze(0)
        inputs = inputs.to(self.device)
        outputs = self.model(inputs)
        _, prediction = torch.max(outputs.data, 1)

        # convert the prediction to a genre
        genre = self.mapping[prediction.item()]

        outputs_list = outputs.data.tolist()[0]

        genres_probs = {self.mapping[i]: round(outputs_list[i], 4) for i in range(len(self.mapping))}

        # return the result
        json_result =  {"genre_top": genre,
                        "genres": genres_probs}
        
        # https://stackoverflow.com/a/57915246
        class NpEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super(NpEncoder, self).default(obj)

        return {
            "result": TaskData(
                data=json.dumps(json_result, cls=NpEncoder),
                type=FieldDescriptionType.APPLICATION_JSON
            )
        }


api_summary = """
Detect the musical genre of a song.
"""

api_description = """
Detect the musical genre of a song. Returns a JSON object with the following fields:
- `genre_top': the top genre of the song
- `genres': a dictionary of the genres of the song with their probabilities
"""

# Define the FastAPI application with information
app = FastAPI(
    title="Musical Genre Detection API.",
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


@app.post('/test')
async def test(audio: UploadFile = File(...)):
    """
    Route to do the speech recognition on the audio file given in the request.
    """
    # Check if audio file is given
    if audio is None:
        raise HTTPException(status_code=400, detail="No audio file given")
    # Check if audio file is valid
    if audio.content_type not in audio_supported:
        raise HTTPException(status_code=400, detail="Invalid audio file given")
    # Save the audio file to the audio folder
    tmp = audio.filename.split('.')
    file_type: str = tmp[len(tmp) - 1]
    try:
        with NamedTemporaryFile(suffix="."+file_type, dir="./audio/", delete=True) as f:
            f.write(await audio.read())
            # Do the speech recognition
            result = my_service.model.transcribe(f.name)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error while processing audio file")

    # Return the result
    return result


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)