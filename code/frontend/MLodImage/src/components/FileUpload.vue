<script setup lang="ts">
import { store } from '@/utils/store';
import { watch } from 'vue';
import { useDropzone } from 'vue3-dropzone';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const {getRootProps, getInputProps, isDragActive, ...rest} = useDropzone({
    onDrop,
    multiple: false,
    accept: '.mp3, .ogg, .wav',
});

watch(store, () => {});

watch(isDragActive, () => {});

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function onDrop(acceptFile: any, rejectReason: any) {
    store.file = acceptFile[0];
    store.disabled = false;
}

function handleClickDeleteFile() {
    store.file = new File([], '');
    store.disabled = true;
}
</script>

<template>
    <div style="height: 100%">
        <div v-if="store.file.name" class="files">
            <div class="file-item p-0">
                <v-chip color="orange" label class="radius-8" size="x-large" prepend-icon="mdi mdi-file-music-outline">
                    <span class="wrap-class">{{ store.file.name }}</span>
                </v-chip>
                <v-btn class="delete-file mt-8" elevation="1" size="large" @click="handleClickDeleteFile()" prepend-icon="mdi mdi-delete">
                    Delete
                </v-btn>
            </div>
        </div>
        <div v-else class="dropzone" v-bind="getRootProps()">
            <div
                    class="border text-grey"
                    :class="{
                    isDragActive,
                }"
            >
                <input v-bind="getInputProps()" />
                <p v-if="isDragActive">Drop the music file here ...</p>
                <p v-else>Drag and drop a music file here, or Click to select file</p>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.dropzone,
.files {
  width: 100%;
  height: 100%;
  margin: 0 auto;
  padding: 10px;
  border-radius: 8px;
  box-shadow: rgba(60, 64, 67, 0.3) 0 1px 2px 0,
  rgba(60, 64, 67, 0.15) 0 1px 3px 1px;
  font-size: 12px;
  background-color: #fff;
  line-height: 1.5;
}

.border {
  height: 100%;
  border: 2px dashed #ccc !important;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  transition: all 0.3s ease;
  background: #fff;

  &.isDragActive {
    border: 2px dashed orange !important;
    color: #000000;
  }
}

.file-item {
  height: 100%;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 7px 7px 7px 7px;
  margin-top: 10px;
  color: darkslategrey;
  font-size: large;

  &:first-child {
    margin-top: 0;
  }

  .delete-file {
    background: red;
    color: #fff;
    padding: 5px 10px;
    border-radius: 8px;
    cursor: pointer;
  }
}

.wrap-class {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: calc(100vw - 140px);
}
</style>
