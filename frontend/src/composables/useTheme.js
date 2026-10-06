import { ref, watch } from 'vue'

const THEMES = [
    { id: 'crimson', label: 'Crimson', hint: 'Чёрный / красный' },
    { id: 'mono', label: 'Mono', hint: 'Жёсткий красный' },
    { id: 'ivory', label: 'Ivory', hint: 'Чистый ч/б' },
    { id: 'slate', label: 'Slate', hint: 'Холодный' },
]

const STORAGE_KEY = 'ge-theme'
const theme = ref('crimson')

function apply(id) {
    const next = THEMES.some((t) => t.id === id) ? id : 'crimson'
    theme.value = next
    document.documentElement.setAttribute('data-theme', next)
    try {
        localStorage.setItem(STORAGE_KEY, next)
    } catch {
        /* private mode */
    }
}

function initTheme() {
    let saved = 'crimson'
    try {
        saved = localStorage.getItem(STORAGE_KEY) || 'crimson'
    } catch {
        /* */
    }
    apply(saved)
}

// один раз при импорте модуля
if (typeof document !== 'undefined') {
    initTheme()
}

export function useTheme() {
    return {
        theme,
        themes: THEMES,
        setTheme: apply,
        initTheme,
    }
}