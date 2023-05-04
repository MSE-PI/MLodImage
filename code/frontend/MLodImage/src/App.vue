<script setup lang="ts">
import { Status, StatusMessage, store } from '@/utils/store';
import { get, getResults, post } from './utils/api';
import LoadingComponent from '@/components/LoadingComponent.vue';
import FileUpload from '@/components/FileUpload.vue';
import JSZip from 'jszip';

const TIMEOUT = 100;

const resetStore = () => {
    store.file = new File([], '');
    store.disabled = true;
    store.execution_id = '';
    store.status = Status.IDLE;
    store.status_message = StatusMessage.IDLE;
    store.progress = 0;
};

const adaptProgress = (status: Status) => {
    switch (status) {
        case Status.WAITING:
            return 0;
        case Status.RUNNING_WHISPER:
            return 20;
        case Status.RUNNING_SENTIMENT:
            return 40;
        case Status.RUNNING_MUSIC_STYLE:
            return 60;
        case Status.RUNNING_IMAGE_GENERATION:
            return 80;
        case Status.FINISHED:
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
        case Status.RUNNING_WHISPER:
            return StatusMessage.RUNNING_WHISPER;
        case Status.RUNNING_SENTIMENT:
            return StatusMessage.RUNNING_SENTIMENT;
        case Status.RUNNING_MUSIC_STYLE:
            return StatusMessage.RUNNING_MUSIC_STYLE;
        case Status.RUNNING_IMAGE_GENERATION:
            return StatusMessage.RUNNING_IMAGE_GENERATION;
        case Status.FINISHED:
            return StatusMessage.FINISHED;
        case Status.FAILED:
            return StatusMessage.FAILED;
        default:
            return StatusMessage.IDLE;
    }
};

const waitForResult = async () => {
    const result = await get(`https://orchestrator-mlodimage.kube.isc.heia-fr.ch/status/${store.execution_id}`);
    if (!result) {
        setTimeout(waitForResult, TIMEOUT);
        store.status = Status.FAILED;
        store.status_message = changeStatusMessage(Status.FAILED);
        store.progress = adaptProgress(Status.FAILED);
        return;
    } else {
        store.status = result;
        store.status_message = changeStatusMessage(result);
        store.progress = adaptProgress(store.status);
        if (store.status == Status.FINISHED) {
            setTimeout(getResult, TIMEOUT);
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
        return;
    } else {
        store.status = result.status;
        store.status_message = changeStatusMessage(result.status);
        if (result.status == Status.WAITING) {
            setTimeout(waitForResult, TIMEOUT);
            return;
        }
    }
};

const handleClick = async () => {
    store.disabled = true;
    const result = await post('https://orchestrator-mlodimage.kube.isc.heia-fr.ch/create', store.file!);
    if (result) {
        store.execution_id = result.id;
        store.status = result.status;
        store.status_message = changeStatusMessage(result.status);
        launchPipeline();
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
                            height="50vh"
                            class="mx-auto gradient radius-8 card-container"
                            elevation="10"
                    >
                        <v-card-title class="headline card">
                            MLodImage
                            <v-icon icon="mdi mdi-play-circle"/>
                        </v-card-title>
                        <v-card-text
                                v-if="
                                store.status == Status.CREATED ||
                                store.status == Status.WAITING ||
                                store.status == Status.RUNNING_WHISPER ||
                                store.status == Status.RUNNING_MUSIC_STYLE ||
                                store.status == Status.RUNNING_SENTIMENT ||
                                store.status == Status.RUNNING_IMAGE_GENERATION"
                                class="card card-middle pb-2"
                        >
                            <v-progress-linear
                                    class="radius-8"
                                    v-model="store.progress"
                                    :buffer-value="store.progress"
                                    color="orange"
                                    height="10"
                            />
                            <v-chip
                                    color="orange"
                                    text-color="white"
                                    class="card mt-2"
                                    size="x-large"
                            >
                                {{ store.status_message }}
                            </v-chip>
                            <LoadingComponent/>
                        </v-card-text>
                        <v-card-text
                                v-else-if="store.status == Status.FINISHED || store.status == Status.FAILED"
                                class="card card-middle pb-2">
                            <v-carousel
                                    v-if="store.status == Status.FINISHED && store.result.images.length > 0"
                                    hide-delimiters
                                    sm="12"
                                    class="radius-8"
                                    show-arrows="hover"
                            >
                                <v-carousel-item
                                        v-for="(image, index) in store.result.images"
                                        :key="index"
                                        :src="image"
                                />
                            </v-carousel>
                            <v-chip
                                    v-if="store.status == Status.FAILED"
                                    color="red"
                                    text-color="white"
                                    class="card"
                            >
                                Error
                            </v-chip>
                        </v-card-text>
                        <v-card-text v-else class="card card-middle pb-2">
                            <FileUpload/>
                        </v-card-text>
                        <v-card-actions class="pl-4 pr-4 pb-4 card">
                            <v-row v-if="store.status == Status.FINISHED || store.status == Status.FAILED">
                                <v-col
                                        cols="9"
                                        class="pr-0"
                                        v-if="store.status == Status.FINISHED"
                                >
                                    <v-btn
                                            elevation="2"
                                            color="success"
                                            variant="flat"
                                            size="x-large"
                                            class="radius-8"
                                            block
                                            v-bind="store"
                                            @click="downloadAll"
                                            prepend-icon="mdi mdi-download"
                                            icon=""
                                    >
                                        Download
                                    </v-btn>
                                </v-col>
                                <v-col>
                                    <v-btn
                                            elevation="2"
                                            color="orange"
                                            variant="flat"
                                            size="x-large"
                                            class="radius-8"
                                            v-bind="store"
                                            block
                                            @click="resetStore"
                                            icon="mdi mdi-refresh"
                                    >
                                    </v-btn>
                                </v-col>
                            </v-row>
                            <v-row
                                    v-if="store.status != Status.FINISHED && store.status != Status.FAILED">
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
                                            icon=""
                                            prepend-icon="mdi mdi-play-circle"
                                    >
                                        Launch
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
