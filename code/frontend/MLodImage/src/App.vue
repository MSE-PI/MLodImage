<script setup lang="ts">
import { MessageColor, MessageIcon, Status, StatusMessage, store } from '@/utils/store';
import { get, getResults, postFile, postURL } from './utils/api';
import FileUpload from '@/components/FileUpload.vue';
import JSZip from 'jszip';

const isMobile = () => {
    return window.innerWidth <= 768;
};
const ORCHESTRATOR_URL = 'orchestrator-mlodimage.kube.isc.heia-fr.ch';
let ws: WebSocket;

const initWebSocket = () => {
    // on localhost, use ws:// instead of wss://
    ws = new WebSocket(`wss://${ORCHESTRATOR_URL}/ws/${store.execution_id}`);

    ws.onopen = () => {
        console.log(`WebSocket Client Connected with execution_id ${store.execution_id}`);
    };

    ws.onclose = () => {
        console.log('WebSocket Client Disconnected');
    };

    ws.onerror = (e) => {
        console.log('Connection Error', e);
    };

    ws.onmessage = (msg) => {
        const message = JSON.parse(msg.data);
        setStatus(message.status);
        if (message.status == Status.RESULT_READY) {
            store.intermediate_results.image_generation_models.value = JSON.parse(message.results.image_generation.model_ids);
            store.intermediate_results.image_generation.value = JSON.stringify(message.results.image_generation);
            getResult();
        } else if (message.status == Status.FAILED) {
            store.disabled = false;
        } else {
            if (message.results && message.results.whisper) {
                store.intermediate_results.whisper.value = message.results.whisper;
            }
            if (message.results && message.results.sentiment_analysis) {
                store.intermediate_results.sentiment.value = message.results.sentiment_analysis;
            }
            if (message.results && message.results.music_style) {
                store.intermediate_results.music_style.value = message.results.music_style;
            }
            if (message.results) {
                console.log('message.results: ', message.results)
            }
        }
    };
}

const setStatus = (status: any) => {
    store.status = status;
    store.progress = adaptProgress(status);
    store.status_message = changeStatusMessage(status);
    store.message_icon = changeStatusIcon(status);
    store.message_color = changeMessageColor(status);
};

const resetStore = () => {
    store.url = '';
    store.file = new File([], '');
    store.disabled = true;
    store.execution_id = '';
    store.result = {
        zip_file: new Blob(),
        images: [],
    };
    store.intermediate_results = {
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
    };
    store.status = Status.IDLE;
    store.status_message = StatusMessage.IDLE;
    store.message_icon = MessageIcon.IDLE;
    store.message_color = MessageColor.IDLE;
    store.progress = 0;
    store.window_page = "run";
    setStatus(Status.IDLE);
    if (ws) {
        ws.close();
    }
};

const adaptProgress = (status: Status) => {
    switch (status) {
        case Status.WAITING:
            return 0;
        case Status.RUNNING_YOUTUBE_DOWNLOADER:
            return 17;
        case Status.RUNNING_WHISPER:
            return 34;
        case Status.RUNNING_SENTIMENT:
            return 51;
        case Status.RUNNING_MUSIC_STYLE:
            return 68;
        case Status.RUNNING_IMAGE_GENERATION:
            return 85;
        case Status.RESULT_READY:
            return 100;
        case Status.FAILED:
            return 100;
        default:
            return 0;
    }
};

const changeStatusMessage = (status: Status) => {
    switch (status) {
        case Status.WAITING:
            return StatusMessage.WAITING;
        case Status.RUNNING_YOUTUBE_DOWNLOADER:
            return StatusMessage.RUNNING_YOUTUBE_DOWNLOADER;
        case Status.RUNNING_WHISPER:
            return StatusMessage.RUNNING_WHISPER;
        case Status.RUNNING_SENTIMENT:
            return StatusMessage.RUNNING_SENTIMENT;
        case Status.RUNNING_MUSIC_STYLE:
            return StatusMessage.RUNNING_MUSIC_STYLE;
        case Status.RUNNING_IMAGE_GENERATION:
            return StatusMessage.RUNNING_IMAGE_GENERATION;
        case Status.RESULT_READY:
            return StatusMessage.RESULT_READY;
        case Status.FINISHED:
            return StatusMessage.FINISHED;
        case Status.FAILED:
            return StatusMessage.FAILED;
        default:
            return StatusMessage.IDLE;
    }
};

const changeStatusIcon = (status: Status) => {
    switch (status) {
        case Status.WAITING:
            return MessageIcon.WAITING;
        case Status.RUNNING_YOUTUBE_DOWNLOADER:
            return MessageIcon.RUNNING_YOUTUBE_DOWNLOADER;
        case Status.RUNNING_WHISPER:
            return MessageIcon.RUNNING_WHISPER;
        case Status.RUNNING_SENTIMENT:
            return MessageIcon.RUNNING_SENTIMENT;
        case Status.RUNNING_MUSIC_STYLE:
            return MessageIcon.RUNNING_MUSIC_STYLE;
        case Status.RUNNING_IMAGE_GENERATION:
            return MessageIcon.RUNNING_IMAGE_GENERATION;
        case Status.RESULT_READY:
            return MessageIcon.RESULT_READY;
        case Status.FINISHED:
            return MessageIcon.FINISHED;
        case Status.FAILED:
            return MessageIcon.FAILED;
        default:
            return MessageIcon.IDLE;
    }
};

const changeMessageColor = (status: Status) => {
    switch (status) {
        case Status.WAITING:
            return MessageColor.WAITING;
        case Status.RUNNING_YOUTUBE_DOWNLOADER:
            return MessageColor.RUNNING_YOUTUBE_DOWNLOADER;
        case Status.RUNNING_WHISPER:
            return MessageColor.RUNNING_WHISPER;
        case Status.RUNNING_SENTIMENT:
            return MessageColor.RUNNING_SENTIMENT;
        case Status.RUNNING_MUSIC_STYLE:
            return MessageColor.RUNNING_MUSIC_STYLE;
        case Status.RUNNING_IMAGE_GENERATION:
            return MessageColor.RUNNING_IMAGE_GENERATION;
        case Status.RESULT_READY:
            return MessageColor.RESULT_READY;
        case Status.FINISHED:
            return MessageColor.FINISHED;
        case Status.FAILED:
            return MessageColor.FAILED;
        default:
            return MessageColor.IDLE;
    }
};

const launchPipeline = async () => {
    const result = await get(`https://${ORCHESTRATOR_URL}/run/${store.execution_id}`);
    if (!result) {
        setStatus(Status.FAILED);
        store.disabled = false;
        return;
    } else {
        initWebSocket();
        setStatus(result.status);
    }
};

const handleClick = async () => {
    store.disabled = true;
    let result;
    if (store.file.name.length > 0) {
        result = await postFile(`https://${ORCHESTRATOR_URL}/create`, store.file!);
    } else {
        result = await postURL(`https://${ORCHESTRATOR_URL}/create`, store.url);
    }
    if (result) {
        store.execution_id = result.id;
        setStatus(result.status);
        await launchPipeline();
    } else {
        store.disabled = false;
    }
};

const getResult = async () => {
    const result = await getResults(`https://${ORCHESTRATOR_URL}/result/${store.execution_id}`);
    if (result) {
        store.result.zip_file = result as Blob;
        const zip = new JSZip();
        const blob = new Blob([result as Blob], {type: 'application/zip'});
        const files = await zip.loadAsync(blob);
        const images = [];
        for (const file in files.files) {
            const image = await files.files[file].async('blob');
            images.push(URL.createObjectURL(image));
        }
        // @ts-ignore-next-line
        store.result.images = images;
        store.disabled = false;
        ws.close();
    }
};

const downloadImage = (index: number) => {
    const link = document.createElement('a');
    link.href = store.result.images[index];
    link.download = `result_${index}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

const downloadAll = () => {
    const link = document.createElement('a');
    link.href = URL.createObjectURL(store.result.zip_file);
    link.download = 'result.zip';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

</script>

<template>
    <v-container class="bg-surface-variant full-height centered bg-gradient" fluid>
        <v-layout fill-height>
            <v-row align="center" justify="center">
                <v-col cols="12" sm="8" md="6" lg="4">
                    <v-window
                        v-model="store.window_page"
                        elevation="10"
                    >
                        <v-window-item
                            value="run"
                        >
                            <v-card
                                width="100%"
                                class="mx-auto gradient rounded-lg card-container"
                            >
                                <v-card-title class="headline card">
                                    <img
                                        class="mt-3"
                                        src="@/assets/logo.svg"
                                        alt="logo"/>
                                </v-card-title>
                                <v-card-text
                                    v-if="
                                store.status == Status.CREATED ||
                                store.status == Status.WAITING ||
                                store.status == Status.RUNNING_YOUTUBE_DOWNLOADER ||
                                store.status == Status.RUNNING_WHISPER ||
                                store.status == Status.RUNNING_MUSIC_STYLE ||
                                store.status == Status.RUNNING_SENTIMENT ||
                                store.status == Status.RUNNING_IMAGE_GENERATION"
                                    class="card card-middle"
                                >
                                    <v-row>
                                        <v-col>
                                            <v-progress-linear
                                                class="rounded-lg"
                                                v-model="store.progress"
                                                :buffer-value="store.progress"
                                                color="orange"
                                                height="10"
                                            />
                                            <v-chip
                                                :color="store.message_color"
                                                text-color="white"
                                                class="card mt-2"
                                                size="large"
                                                label
                                                :prepend-icon="store.message_icon"
                                            >
                                                {{ store.status_message }}
                                            </v-chip>
                                        </v-col>
                                    </v-row>
                                    <v-row class="text-center">
                                        <v-col>
                                            <v-progress-circular
                                                class="rounded-lg"
                                                :size="70"
                                                :width="7"
                                                :value="store.progress"
                                                :color="store.message_color"
                                                indeterminate
                                            />
                                        </v-col>
                                    </v-row>
                                </v-card-text>
                                <v-card-text
                                    v-else-if="store.status == Status.RESULT_READY || store.status == Status.FAILED"
                                    class="card card-middle pb-2">
                                    <v-carousel
                                        v-if="store.status == Status.RESULT_READY && store.result.images.length > 0"
                                        hide-delimiters
                                        sm="12"
                                        class="pt-0 rounded-lg"
                                        show-arrows="hover"
                                        style="height: auto"
                                    >
                                        <v-carousel-item
                                            v-for="(image, index) in store.result.images"
                                            :key="index"
                                            :src="image"
                                        >
                                            <v-row class="text-center">
                                                <v-col>
                                                    <div class="title d-flex flex-row card-middle pt-4 pl-4">
                                                        <v-btn color="pink"
                                                               dark
                                                               large
                                                               @click="downloadImage(index)"
                                                               icon="mdi mdi-file-download-outline"
                                                               title="Download image"
                                                        />
                                                    </div>
                                                </v-col>
                                                <v-col>
                                                    <div v-if="isMobile()"
                                                         class="title d-flex flex-row pt-4 pr-4 justify-end">
                                                        <v-snackbar
                                                            :timeout="3000"
                                                            color="white"
                                                            multi-line
                                                        >
                                                            <template v-slot:activator="{ props }">
                                                                <v-btn
                                                                    dark
                                                                    large
                                                                    icon="mdi mdi-brain"
                                                                    title="Image generation model"
                                                                    v-bind="props"
                                                                />
                                                            </template>
                                                            <b>Image generation model:</b>
                                                            <br/>
                                                            {{
                                                                store.intermediate_results.image_generation_models.value[index]
                                                            }}
                                                        </v-snackbar>
                                                    </div>
                                                    <div v-else class="title d-flex flex-row pt-4 pr-4 justify-end">
                                                        <v-chip color="white"
                                                                variant="elevated"
                                                                size="x-large"
                                                                label
                                                                title="Image generation model"
                                                        >
                                                            <v-icon start icon="mdi-brain"></v-icon>
                                                            {{
                                                                store.intermediate_results.image_generation_models.value[index]
                                                            }}
                                                        </v-chip>
                                                    </div>
                                                </v-col>
                                            </v-row>
                                        </v-carousel-item>
                                    </v-carousel>
                                    <v-chip
                                        v-if="store.status == Status.FAILED"
                                        color="red"
                                        text-color="white"
                                        class="card"
                                        size="large"
                                        prepend-icon="mdi mdi-alert-octagon-outline"
                                    >
                                        Error
                                    </v-chip>
                                </v-card-text>
                                <v-card-text v-else class="card card-middle pb-2">
                                    <v-container class="pl-0 pr-0 pb-0 pt-0">
                                        <!--<v-row class="text-center">
                                            <v-col class="pb-0">
                                                <div class="custom-text-field rounded-lg mb-5">
                                                    <v-text-field
                                                        label="YouTube URL"
                                                        color="orange"
                                                        icon="mdi-youtube"
                                                        variant="solo"
                                                        prepend-inner-icon="mdi mdi-youtube"
                                                        @input="store.disabled = store.url.length == 0"
                                                        v-model="store.url"
                                                        :disabled="store.file.name.length > 0"
                                                        class="pb-4"
                                                    />
                                                </div>
                                            </v-col>
                                        </v-row>
                                        <v-row class="text-center mt-1">
                                            <v-col class="text-amber text-h6">
                                                OR
                                            </v-col>
                                        </v-row>-->
                                        <v-row class="text-center">
                                            <v-col>
                                                <FileUpload/>
                                            </v-col>
                                        </v-row>
                                    </v-container>
                                </v-card-text>
                                <v-card-actions class="pl-4 pr-4 pb-4 card">
                                    <v-row v-if="store.status == Status.RESULT_READY || store.status == Status.FAILED">
                                        <v-col
                                            cols="9"
                                            class="pr-0"
                                            v-if="store.status == Status.RESULT_READY"
                                        >
                                            <v-btn
                                                elevation="2"
                                                color="success"
                                                variant="flat"
                                                size="x-large"
                                                class="rounded-lg"
                                                height="100%"
                                                block
                                                v-bind="store"
                                                @click="downloadAll"
                                                prepend-icon="mdi mdi-folder-arrow-down-outline"
                                                title="Download all files"
                                            >
                                                Download
                                            </v-btn>
                                        </v-col>
                                        <v-col>
                                            <v-btn
                                                v-if="store.status == Status.FAILED"
                                                elevation="2"
                                                color="orange"
                                                variant="elevated"
                                                size="x-large"
                                                class="rounded-lg"
                                                block
                                                @click="resetStore"
                                                prepend-icon="mdi mdi-refresh"
                                                title="Reset"
                                            >
                                                Start Over
                                            </v-btn>
                                            <v-btn
                                                v-else
                                                elevation="2"
                                                color="orange"
                                                variant="elevated"
                                                size="large"
                                                class="rounded-lg"
                                                block
                                                @click="resetStore"
                                                icon="mdi mdi-refresh"
                                                title="Reset"
                                            />
                                        </v-col>
                                        <v-divider
                                            class="rounded-lg border-opacity-75 mt-2 mb-2 mr-4 ml-4"
                                            :thickness="3"
                                        />
                                        <v-col cols="12" v-if="store.window_page != 'run'">
                                            <v-btn
                                                elevation="2"
                                                color="green"
                                                variant="flat"
                                                size="x-large"
                                                class="rounded-lg"
                                                block
                                                prepend-icon="mdi mdi-play-circle-outline"
                                                @click="store.window_page = 'run'"
                                            >
                                                Execution
                                            </v-btn>
                                        </v-col>
                                        <v-col cols="12" v-if="store.window_page != 'info'">
                                            <v-btn
                                                elevation="2"
                                                color="blue-grey"
                                                variant="flat"
                                                size="x-large"
                                                class="rounded-lg"
                                                block
                                                prepend-icon="mdi mdi-information-outline"
                                                @click="store.window_page = 'info'"
                                            >
                                                Results
                                            </v-btn>
                                        </v-col>
                                    </v-row>
                                    <v-row v-else>
                                        <v-col
                                            cols="12"
                                        >
                                            <v-btn
                                                elevation="2"
                                                color="orange"
                                                variant="flat"
                                                size="x-large"
                                                class="rounded-lg"
                                                block
                                                v-bind="store"
                                                @click="handleClick"
                                                :prepend-icon="store.status == Status.IDLE ?
                                            'mdi mdi-play' : 'mdi mdi-clock-outline'"
                                            >
                                                {{ store.status == Status.IDLE ? 'Launch' : ' Running...' }}
                                            </v-btn>
                                        </v-col>
                                        <v-divider
                                            v-if="store.status != Status.IDLE"
                                            class="rounded-lg border-opacity-75 mt-2 mb-2 mr-4 ml-4"
                                            :thickness="3"
                                        />
                                        <v-col cols="12" v-if="store.window_page != 'run'">
                                            <v-btn
                                                elevation="2"
                                                color="green"
                                                variant="flat"
                                                size="x-large"
                                                class="rounded-lg"
                                                block
                                                prepend-icon="mdi mdi-play-circle-outline"
                                                @click="store.window_page = 'run'"
                                            >
                                                Execution
                                            </v-btn>
                                        </v-col>
                                        <v-col cols="12" v-if="store.window_page != 'info' &&
                                         store.status != Status.IDLE">
                                            <v-btn
                                                elevation="2"
                                                color="blue-grey"
                                                variant="flat"
                                                size="x-large"
                                                class="rounded-lg"
                                                block
                                                prepend-icon="mdi mdi-information-outline"
                                                @click="store.window_page = 'info'"
                                            >
                                                Results
                                            </v-btn>
                                        </v-col>
                                    </v-row>
                                </v-card-actions>
                            </v-card>
                        </v-window-item>
                        <v-window-item
                            value="info"
                        >
                            <v-card
                                width="100%"
                                class="mx-auto gradient rounded-lg card-container"
                            >
                                <v-card-title class="headline card">
                                    <img
                                        class="mt-3"
                                        src="@/assets/logo.svg"
                                        alt="logo"/>
                                </v-card-title>
                                <v-card-text class="pb-2">
                                    <v-expansion-panels
                                        focusable
                                        class="rounded-lg">
                                        <v-expansion-panel
                                            class="rounded-lg"
                                            id="whisper"
                                            :title="store.intermediate_results.whisper.title"
                                            :disabled="store.intermediate_results.whisper.value=='null'"
                                        >
                                            <v-expansion-panel-text class="custom-expansion-panel">
                                                {{ store.intermediate_results.whisper.value }}
                                            </v-expansion-panel-text>
                                        </v-expansion-panel>
                                        <v-expansion-panel
                                            class="rounded-lg"
                                            id="sentiment"
                                            :title="store.intermediate_results.sentiment.title"
                                            :disabled="store.intermediate_results.sentiment.value=='null'"
                                        >
                                            <v-expansion-panel-text>
                                                <pre class="text-left custom-expansion-panel">
                                                    {{ store.intermediate_results.sentiment.value }}
                                                </pre>
                                            </v-expansion-panel-text>
                                        </v-expansion-panel>
                                        <v-expansion-panel
                                            class="rounded-lg"
                                            id="music_style"
                                            :title="store.intermediate_results.music_style.title"
                                            :disabled="store.intermediate_results.music_style.value=='null'"
                                        >
                                            <v-expansion-panel-text>
                                                <pre class="text-left custom-expansion-panel">
                                                    {{ store.intermediate_results.music_style.value }}
                                                </pre>
                                            </v-expansion-panel-text>
                                        </v-expansion-panel>
                                        <v-expansion-panel
                                            class="rounded-lg"
                                            id="music"
                                            :title="store.intermediate_results.image_generation.title"
                                            :disabled="store.intermediate_results.image_generation.value=='null'"
                                        >
                                            <v-expansion-panel-text>
                                                <pre class="text-left custom-expansion-panel">
                                                    {{ store.intermediate_results.image_generation.value }}
                                                </pre>
                                            </v-expansion-panel-text>
                                        </v-expansion-panel>
                                    </v-expansion-panels>
                                </v-card-text>
                                <v-card-actions class="pl-4 pr-4 pb-4 card">
                                    <v-row>
                                        <v-col cols="12" v-if="store.window_page != 'run'">
                                            <v-btn
                                                elevation="2"
                                                color="light-green"
                                                variant="flat"
                                                size="x-large"
                                                class="rounded-lg"
                                                block
                                                prepend-icon="mdi mdi-play-circle-outline"
                                                @click="store.window_page = 'run'"
                                            >
                                                Execution
                                            </v-btn>
                                        </v-col>
                                        <v-col cols="12" v-if="store.window_page != 'info'">
                                            <v-btn
                                                elevation="2"
                                                color="blue-grey"
                                                variant="flat"
                                                size="x-large"
                                                class="rounded-lg"
                                                block
                                                prepend-icon="mdi mdi-information-outline"
                                                @click="store.window_page = 'info'"
                                            >
                                                Results
                                            </v-btn>
                                        </v-col>
                                    </v-row>
                                </v-card-actions>
                            </v-card>
                        </v-window-item>
                    </v-window>
                </v-col>
            </v-row>
        </v-layout>
    </v-container>
</template>

<style scoped>
.full-height {
    height: 100vh;
    overflow: auto;
}

.card-container {
    display: flex;
    flex-direction: column;
    height: 95%;
}

.card-middle {
    height: 100%;
}

.card {
    height: auto;
}

.centered {
    display: flex;
    align-items: center;
    justify-content: center;
}

.bg-gradient {
    background: linear-gradient(15deg, #13547a 0%, #80d0c7 100%);
}

.gradient {
    background: linear-gradient(109.6deg, rgb(0, 37, 84) 11.2%, rgba(0, 37, 84, 0.32) 100.2%);
    color: white;
}

.custom-expansion-panel {
    white-space: pre-wrap;
    word-wrap: break-word;
    max-width: 100%;
}

@media (max-width: 600px) {
    .custom-expansion-panel {
        max-width: 326px;
    }
}

.custom-text-field {
    overflow: hidden;
    height: 56px;
}
</style>
