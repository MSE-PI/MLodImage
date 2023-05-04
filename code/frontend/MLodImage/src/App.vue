<script setup lang="ts">
import { store } from '@/utils/store';
import { post, get } from './utils/api';
import LoadingComponent from '@/components/LoadingComponent.vue';
import FileUpload from '@/components/FileUpload.vue';

const waitForResult = async (id: string) => {
    const result = await get(`http://localhost:8080/tasks/${id}/status`);
    if (!result) {
        setTimeout(waitForResult, 1000);
        return;
    } else {
        console.log(result);
        store.disabled = false;
    }
};

const handleClick = async () => {
    store.disabled = true;
    const result = await post('https://whisper-mlodimage.kube.isc.heia-fr.ch/test', store.file!);
    if (result) {
        console.log(result);
        //waitForResult(result.id);
    } else {
        console.log(result);
    }
    store.disabled = false;
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
                        <v-card-text v-if="!store.disabled || !store.file.name" class="card card-middle pb-2">
                            <FileUpload />
                        </v-card-text>
                        <v-card-text v-else class="card card-middle pb-2">
                            <!--<v-progress-circular
                                indeterminate
                                color="orange"
                                size="64"
                            ></v-progress-circular>-->
                            <LoadingComponent />
                        </v-card-text>
                        <v-card-actions class="pl-4 pr-4 pb-4 card">
                            <v-btn
                                elevation="2"
                                color="orange"
                                variant="flat"
                                size="x-large"
                                class="radius-8"
                                block
                                v-bind="store"
                                @click="handleClick"
                            >
                                Launch
                            </v-btn>
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
