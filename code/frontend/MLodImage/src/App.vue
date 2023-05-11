<script setup lang="ts">
import { Status, StatusMessage, MessageIcon, MessageColor, store } from '@/utils/store';
import { get, getResults, postFile, postURL } from './utils/api';
import FileUpload from '@/components/FileUpload.vue';
import JSZip from 'jszip';
import { WebSocket } from 'vite';

const TIMEOUT = 100;
let ws: WebSocket;

const initWebSocket = () => {
    ws = new WebSocket(`wss://orchestrator-mlodimage.kube.isc.heia-fr.ch/ws/${store.execution_id}`);

    ws.on("open", () => {
        console.log("Connected to orchestrator");
    });
    ws.on("message", (data: any) => {
        const message = JSON.parse(data);
        setStatus(message.status);
        if (message.status == Status.RESULT_READY) {
            getResult();
        } else if (message.status == Status.FAILED) {
            store.disabled = false;
        } else {
            console.log(message);
        }
    });
    ws.on("close", () => {
        console.log('Connection closed');
    });
    ws.on("error", (err: any) => {
        console.log(err);
    });
}

const setStatus = (status: Status) => {
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
    setStatus(Status.IDLE);
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

const waitForResult = async () => {
    const result = await get(`https://orchestrator-mlodimage.kube.isc.heia-fr.ch/status/${store.execution_id}`);
    if (!result) {
        setTimeout(waitForResult, TIMEOUT);
        setStatus(Status.FAILED);
        store.disabled = false;
        return;
    } else {
        setStatus(result);
        if (store.status == Status.RESULT_READY) {
            getResult();
            return;
        } else if (store.status == Status.FAILED) {
            return;
        } else {
            setTimeout(waitForResult, TIMEOUT);
            return;
        }
    }
};

const launchPipeline = async () => {
    const result = await get(`https://orchestrator-mlodimage.kube.isc.heia-fr.ch/run/${store.execution_id}`);
    if (!result) {
        setStatus(Status.FAILED);
        store.disabled = false;
        return;
    } else {
        setStatus(result.status);
        if (result.status == Status.WAITING) {
            setTimeout(waitForResult, TIMEOUT);
            return;
        }
    }
};

const handleClick = async () => {
    store.disabled = true;
    let result;
    if (store.file.name.length > 0) {
        result = await postFile('https://orchestrator-mlodimage.kube.isc.heia-fr.ch/create', store.file!);
    } else {
        result = await postURL('https://orchestrator-mlodimage.kube.isc.heia-fr.ch/create', store.url);
    }
    if (result) {
        store.execution_id = result.id;
        setStatus(result.status);
        // launchPipeline();
        initWebSocket();
    } else {
        store.disabled = false;
    }
};

const getResult = async () => {
    const result = await getResults(`https://orchestrator-mlodimage.kube.isc.heia-fr.ch/result/${store.execution_id}`);
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
                    <v-card
                            width="100%"
                            class="mx-auto gradient radius-8 card-container"
                            elevation="10"
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
                                            class="radius-8"
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
                                            class="radius-8"
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
                                    class="pt-0 radius-8"
                                    show-arrows="hover"
                                    style="height: auto"
                            >
                                <v-carousel-item
                                        v-for="(image, index) in store.result.images"
                                        :key="index"
                                        :src="image"
                                >
                                    <div class="title d-flex flex-row card-middle pt-4 pl-4">
                                        <v-btn color="pink"
                                               dark
                                               large
                                               @click="downloadImage(index)"
                                               icon="mdi mdi-file-download-outline"
                                               title="Download image"
                                        />
                                    </div>
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
                                <v-row class="text-center">
                                    <v-col class="pb-0">
                                        <v-text-field
                                                label="YouTube URL"
                                                icon="mdi-youtube"
                                                variant="solo"
                                                class="radius-8"
                                                prepend-inner-icon="mdi mdi-youtube"
                                                @input="store.disabled = store.url.length == 0"
                                                v-model="store.url"
                                                :disabled="store.file.name.length > 0"
                                        ></v-text-field>
                                    </v-col>
                                </v-row>
                                <v-row class="text-center mt-1">
                                    <v-col class="text-amber text-h6">
                                        OR
                                    </v-col>
                                </v-row>
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
                                            class="radius-8"
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
                                            size="large"
                                            class="radius-8"
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
                                            class="radius-8"
                                            block
                                            @click="resetStore"
                                            icon="mdi mdi-refresh"
                                            title="Reset"
                                    />
                                </v-col>
                            </v-row>
                            <v-row
                                    v-if="store.status != Status.RESULT_READY && store.status != Status.FAILED">
                                <v-col>
                                    <v-btn
                                            elevation="2"
                                            color="orange"
                                            variant="flat"
                                            size="x-large"
                                            class="radius-8"
                                            block
                                            v-bind="store"
                                            @click="handleClick"
                                            :prepend-icon="store.status == Status.IDLE ?
                                            'mdi mdi-play-box-outline' : 'mdi mdi-clock-outline'"
                                    >
                                        {{ store.status == Status.IDLE ? 'Launch' : ' Running...' }}
                                    </v-btn>
                                </v-col>
                            </v-row>
                        </v-card-actions>
                    </v-card>
                </v-col>
            </v-row>
        </v-layout>
    </v-container>
</template>

<style scoped>
.full-height {
    height: 100vh;
}

.card-container {
    display: flex;
    flex-direction: column;
    height: 100%;
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

.radius-8 {
    border-radius: 8px;
}
</style>
