<script setup>
import { ref } from 'vue'
import { lfgApi } from '../../api/lfg'
import GameSelect from './GameSelect.vue'
import IconCalendar from '../icons/IconCalendar.vue'

const emit = defineEmits(['close', 'created'])

const form = ref({ game: '', datetime: '', description: '', contact: '', slots_needed: 1 })
const errors = ref({})
const submitting = ref(false)

async function submit() {
  submitting.value = true
  errors.value = {}
  try {
    const payload = { ...form.value, datetime: new Date(form.value.datetime).toISOString() }
    const res = await lfgApi.create(payload)
    emit('created', res.data)
    emit('close')
  } catch (e) {
    errors.value = e.response?.data || { detail: 'Не удалось создать заявку' }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="modal card fade-in-up">
      <div class="modal-header">
        <h3>Новая заявка</h3>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <form @submit.prevent="submit" class="form">
        <label>
          Игра
          <GameSelect v-model="form.game" />
          <span class="error" v-if="errors.game">{{ errors.game[0] }}</span>
        </label>

        <label>
          Дата и время
          <div class="datetime-wrap">
            <input v-model="form.datetime" type="datetime-local" class="datetime-input" />
            <span class="datetime-icon"><IconCalendar /></span>
          </div>
        </label>

        <label>
          Сколько игроков нужно
          <input v-model.number="form.slots_needed" type="number" min="1" max="20" />
          <span class="error" v-if="errors.slots_needed">{{ errors.slots_needed[0] }}</span>
        </label>

        <label>
          Описание
          <textarea v-model="form.description" rows="3" placeholder="Нужен саппорт, ранг от Diamond..."></textarea>
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
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.65); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal { width: 440px; max-width: 90vw; max-height: 88vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.modal-header h3 { margin: 0; }
.close-btn { background: none; border: none; color: var(--text-secondary); font-size: 16px; cursor: pointer; }
.form { display: flex; flex-direction: column; gap: 14px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--text-secondary); }
input, textarea { background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 10px 12px; color: var(--text-primary); font-size: 14px; font-family: inherit; resize: vertical; }
input:focus, textarea:focus { outline: none; border-color: var(--accent); }
.hint { font-size: 11px; color: var(--text-muted); }
.error { color: var(--danger); font-size: 12px; }
.datetime-wrap { position: relative; }
.datetime-icon {
  position: absolute; right: 12px; top: 50%; transform: translateY(-50%);
  pointer-events: none; color: var(--accent);
}
.datetime-icon svg { width: 17px; height: 17px; }
.datetime-input {
  color-scheme: dark;
  background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-sm);
  padding: 10px 40px 10px 12px; color: var(--text-primary); font-size: 14px; width: 100%;
}
.datetime-input::-webkit-calendar-picker-indicator { opacity: 0; position: absolute; right: 0; width: 40px; height: 100%; cursor: pointer; }
</style>