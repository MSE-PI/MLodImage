import { reactive } from 'vue';

export const enum Status {
    IDLE = "idle",
    CREATED = "created",
    WAITING = "waiting",
    RUNNING_YOUTUBE_DOWNLOADER = "running_youtube_downloader",
    RUNNING_WHISPER = "running_whisper",
    RUNNING_SENTIMENT = "running_sentiment",
    RUNNING_MUSIC_STYLE = "running_music_style",
    RUNNING_IMAGE_GENERATION = "running_image_generation",
    RESULT_READY = "result_ready",
    FINISHED = "finished",
    FAILED = "failed",
}

export const enum StatusMessage {
    IDLE = "Idle",
    CREATED = "Pipeline created",
    WAITING = "Waiting for execution",
    RUNNING_YOUTUBE_DOWNLOADER = "Downloading audio from YouTube",
    RUNNING_WHISPER = "Recognizing text from audio",
    RUNNING_SENTIMENT = "Extracting sentiment and topics",
    RUNNING_MUSIC_STYLE = "Detecting music style",
    RUNNING_IMAGE_GENERATION = "Generating images",
    RESULT_READY = "Finished",
    FINISHED = "Finished",
    FAILED = "Failed",
}

export const enum MessageIcon {
    IDLE = "mdi mdi-clock-outline",
    CREATED = "mdi mdi-check",
    WAITING = "mdi mdi-clock-outline",
    RUNNING_YOUTUBE_DOWNLOADER = "mdi mdi-youtube",
    RUNNING_WHISPER = "mdi mdi-account-voice",
    RUNNING_SENTIMENT = "mdi mdi-emoticon-happy-outline",
    RUNNING_MUSIC_STYLE = "mdi mdi-music-note-outline",
    RUNNING_IMAGE_GENERATION = "mdi mdi-image-outline",
    RESULT_READY = "mdi mdi-check-circle-outline",
    FINISHED = "mdi mdi-check-circle-outline",
    FAILED = "mdi mdi-close-circle-outline",
}

export const enum MessageColor {
    IDLE = "grey",
    CREATED = "green",
    WAITING = "grey",
    RUNNING_YOUTUBE_DOWNLOADER = "red",
    RUNNING_WHISPER = "amber",
    RUNNING_SENTIMENT = "orange",
    RUNNING_MUSIC_STYLE = "purple",
    RUNNING_IMAGE_GENERATION = "blue",
    RESULT_READY = "green",
    FINISHED = "green",
    FAILED = "red",
}

export const store = reactive({
    disabled: true,
    url: '',
    file: new File([], ''),
    execution_id: '',
    result: {
        zip_file: new Blob(),
        images: [],
    },
    intermediate_results: {
        whisper: {
            title: "Text Recognition",
            value: 'null',
        },
        sentiment: {
            title: "Sentiment Analysis",
            value: 'null',
        },
        music_style: {
            title: "Music Style Detection",
            value: 'null',
        },
        image_generation: {
            title: "Image Generation",
            value: 'null',
        },
        image_generation_models: {
            title: "Image Generation Models",
            value: [],
        }
    },
    status: Status.IDLE,
    status_message: StatusMessage.IDLE,
    message_icon: MessageIcon.IDLE,
    message_color: MessageColor.IDLE,
    progress: 0,
    window_page: "run",
});
