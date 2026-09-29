<script setup>
import { ref, onMounted } from 'vue'
import { lfgApi } from '../../api/lfg'
import GameSelect from './GameSelect.vue'
import IconCalendar from '../icons/IconCalendar.vue'
import { useToast } from '../../composables/useToast'

const emit = defineEmits(['close', 'created'])
const toast = useToast()

const form = ref({
  game: '',
  description: '',
  contact: '',
  slots_needed: 1,
})
const datePart = ref('')
const timePart = ref('20:00')
const errors = ref({})
const submitting = ref(false)

function pad(n) {
  return String(n).padStart(2, '0')
}

function toLocalParts(d) {
  return {
    date: `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`,
    time: `${pad(d.getHours())}:${pad(d.getMinutes())}`,
  }
}

function setDefaults() {
  const d = new Date()
  d.setSeconds(0, 0)
  d.setMinutes(0)
  d.setHours(d.getHours() + 1)
  const p = toLocalParts(d)
  datePart.value = p.date
  timePart.value = p.time
}

function applyPreset(kind) {
  const d = new Date()
  d.setSeconds(0, 0)
  d.setMinutes(0)

  if (kind === '1h') {
    d.setHours(d.getHours() + 1)
  } else if (kind === 'evening') {
    d.setHours(20, 0, 0, 0)
    if (d <= new Date()) d.setDate(d.getDate() + 1)
  } else if (kind === 'tomorrow') {
    d.setDate(d.getDate() + 1)
    d.setHours(18, 0, 0, 0)
  }

  const p = toLocalParts(d)
  datePart.value = p.date
  timePart.value = p.time
}

function buildIso() {
  if (!datePart.value || !timePart.value) return null
  const local = new Date(`${datePart.value}T${timePart.value}:00`)
  if (Number.isNaN(local.getTime())) return null
  return local.toISOString()
}

async function submit() {
  submitting.value = true
  errors.value = {}

  const iso = buildIso()
  if (!iso) {
    errors.value = { datetime: ['Укажи дату и время'] }
    submitting.value = false
    return
  }
  if (new Date(iso) < new Date()) {
    errors.value = { datetime: ['Нельзя создать заявку на прошедшее время'] }
    submitting.value = false
    return
  }

  try {
    const payload = {
      ...form.value,
      datetime: iso,
    }
    const res = await lfgApi.create(payload)
    emit('created', res.data)
    emit('close')
    toast.success('Заявка опубликована')
  } catch (e) {
    errors.value = e.response?.data || { detail: 'Не удалось создать заявку' }
    const msg =
      e.response?.data?.detail ||
      (typeof e.response?.data === 'object' ? 'Проверь поля формы' : null) ||
      'Не удалось создать заявку'
    toast.error(typeof msg === 'string' ? msg : 'Не удалось создать заявку')
  } finally {
    submitting.value = false
  }
}

onMounted(setDefaults)
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="modal card fade-in-up">
      <div class="modal-header">
        <h3>Новая заявка</h3>
        <button type="button" class="close-btn" @click="emit('close')">✕</button>
      </div>

      <form @submit.prevent="submit" class="form">
        <label>
          Игра
          <GameSelect v-model="form.game" />
          <span class="error" v-if="errors.game">{{ errors.game[0] }}</span>
        </label>

        <div class="when-block">
          <span class="when-label">Когда играем</span>
          <div class="presets">
            <button type="button" class="preset" @click="applyPreset('1h')">Через час</button>
            <button type="button" class="preset" @click="applyPreset('evening')">Сегодня 20:00</button>
            <button type="button" class="preset" @click="applyPreset('tomorrow')">Завтра 18:00</button>
          </div>
          <div class="when-row">
            <label class="mini">
              Дата
              <div class="datetime-wrap">
                <input v-model="datePart" type="date" class="datetime-input" required />
                <span class="datetime-icon"><IconCalendar /></span>
              </div>
            </label>
            <label class="mini">
              Время
              <input v-model="timePart" type="time" class="datetime-input time-only" required />
            </label>
          </div>
          <span class="error" v-if="errors.datetime">{{ errors.datetime[0] }}</span>
        </div>

        <label>
          Сколько игроков нужно
          <input v-model.number="form.slots_needed" type="number" min="1" max="20" />
          <span class="error" v-if="errors.slots_needed">{{ errors.slots_needed[0] }}</span>
        </label>

        <label>
          Описание
          <textarea
            v-model="form.description"
            rows="3"
            placeholder="Нужен саппорт, ранг от Diamond..."
          ></textarea>
          <span class="error" v-if="errors.description">{{ errors.description[0] }}</span>
        </label>

        <label>
          Контакт
          <input v-model="form.contact" placeholder="Discord: name#0000" />
          <span class="hint">Виден только тем, кто откликнется — так меньше спама</span>
          <span class="error" v-if="errors.contact">{{ errors.contact[0] }}</span>
        </label>

        <span class="error" v-if="errors.detail">{{ errors.detail }}</span>

        <button type="submit" class="btn-primary" :disabled="submitting">
          {{ submitting ? 'Создаём...' : 'Опубликовать заявку' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  z-index: 100;
  padding: max(32px, 6vh) 16px 48px;
  overflow-y: auto;
}
.modal {
  width: 440px;
  max-width: 90vw;
  margin: 0 auto;
  flex-shrink: 0;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.modal-header h3 { margin: 0; }
.close-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 600;
}
input,
textarea {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  color: var(--text-primary);
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  font-weight: 500;
}
input:focus,
textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(230, 57, 70, 0.12);
}
.hint { font-size: 11px; color: var(--text-muted); font-weight: 500; }
.error { color: var(--danger); font-size: 12px; font-weight: 500; }

.when-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.when-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 600;
}
.presets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.preset {
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 700;
  padding: 6px 10px;
  border-radius: 999px;
  cursor: pointer;
}
.preset:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-dim);
}
.when-row {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 10px;
}
.mini { margin: 0; }

.datetime-wrap { position: relative; }
.datetime-icon {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: var(--accent);
}
.datetime-icon svg { width: 17px; height: 17px; }
.datetime-input {
  color-scheme: dark;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 40px 10px 12px;
  color: var(--text-primary);
  font-size: 14px;
  width: 100%;
  font-variant-numeric: tabular-nums;
}
.time-only { padding-right: 12px; }
.datetime-input::-webkit-calendar-picker-indicator {
  opacity: 0;
  position: absolute;
  right: 0;
  width: 40px;
  height: 100%;
  cursor: pointer;
}

.btn-primary {
  background: var(--accent);
  color: #fff;
  border: none;
  padding: 12px;
  border-radius: var(--radius-sm);
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  margin-top: 4px;
}
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
</style>