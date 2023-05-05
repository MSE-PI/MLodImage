import { reactive } from 'vue';

export const enum Status {
    IDLE = "idle",
    CREATED = "created",
    WAITING = "waiting",
    RUNNING_WHISPER = "running_whisper",
    RUNNING_SENTIMENT = "running_sentiment",
    RUNNING_MUSIC_STYLE = "running_music_style",
    RUNNING_IMAGE_GENERATION = "running_image_generation",
    FINISHED = "finished",
    FAILED = "failed",
}

export const enum StatusMessage {
    IDLE = "Idle",
    CREATED = "Pipeline created",
    WAITING = "Waiting for execution",
    RUNNING_WHISPER = "Recognizing text from audio",
    RUNNING_SENTIMENT = "Extracting sentiment and topic from text",
    RUNNING_MUSIC_STYLE = "Detecting music style",
    RUNNING_IMAGE_GENERATION = "Generating images",
    FINISHED = "Finished",
    FAILED = "Failed",
}

export const enum MessageIcon {
    IDLE = "mdi mdi-clock-outline",
    CREATED = "mdi mdi-check",
    WAITING = "mdi mdi-clock-outline",
    RUNNING_WHISPER = "mdi mdi-account-voice",
    RUNNING_SENTIMENT = "mdi mdi-emoticon-happy-outline",
    RUNNING_MUSIC_STYLE = "mdi mdi-music-note-outline",
    RUNNING_IMAGE_GENERATION = "mdi mdi-image-outline",
    FINISHED = "mdi mdi-check-circle-outline",
    FAILED = "mdi mdi-close-circle-outline",
}

export const enum MessageColor {
    IDLE = "grey",
    CREATED = "green",
    WAITING = "grey",
    RUNNING_WHISPER = "Red",
    RUNNING_SENTIMENT = "orange",
    RUNNING_MUSIC_STYLE = "pink",
    RUNNING_IMAGE_GENERATION = "blue",
    FINISHED = "green",
    FAILED = "red",
}

export const store = reactive({
    disabled: true,
    file: new File([], ''),
    execution_id: '',
    result: {
        zip_file: new Blob(),
        images: [],
    },
    status: Status.IDLE,
    status_message: StatusMessage.IDLE,
    message_icon: MessageIcon.IDLE,
    message_color: MessageColor.IDLE,
    progress: 0,
});
