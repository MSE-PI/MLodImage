<script setup lang="ts">
</script>

<template>
    <v-container class="bg-surface-variant full-height centered bg-gradient" fluid>
        <v-layout fill-height>
            <v-row align="center" justify="center">
                <v-col cols="12" sm="8" md="6" lg="4">
                    <v-card
                            width="100%"
                            height="50vh"
                            class="mx-auto gradient radius-10"
                            elevation="10"
                            transition="scale-transition"
                    >
                        <v-card-title class="headline">MLodImage</v-card-title>
                        <v-card-text>
                            <v-file-input
                                    prepend-icon=""
                                    variant="solo"
                                    accept="audio/ogg,audio/mp3"
                                    label="File input"
                            ></v-file-input>
                        </v-card-text>
                        <v-card-actions>
                            <v-btn
                                    color="orange"
                                    variant="flat"
                                    size="x-large"
                                    prepend-icon="mdi-play"
                                    block
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

.radius-10 {
    border-radius: 10px;
}
</style>
