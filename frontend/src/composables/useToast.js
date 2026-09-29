import { ref } from 'vue'

const toasts = ref([])
let seq = 0

export function useToast() {
    function push(message, type = 'error', ms = 4200) {
        const id = ++seq
        toasts.value = [...toasts.value, { id, message, type }]
        setTimeout(() => {
            toasts.value = toasts.value.filter((t) => t.id !== id)
        }, ms)
    }

    return {
        toasts,
        error: (msg) => push(msg, 'error'),
        success: (msg) => push(msg, 'success'),
        info: (msg) => push(msg, 'info'),
        dismiss: (id) => {
            toasts.value = toasts.value.filter((t) => t.id !== id)
        },
    }
}