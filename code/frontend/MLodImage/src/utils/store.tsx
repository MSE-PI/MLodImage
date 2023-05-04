import { reactive } from 'vue';

export const store = reactive({
    disabled: true,
    file: new File([], ''),
});
