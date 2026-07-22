<script setup>
import { ref, computed } from 'vue'
import { GAMES, getGameColor, getGameInitials } from '../../constants/games'

const props = defineProps({ modelValue: String })
const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const search = ref('')

const filtered = computed(() =>
  GAMES.filter(g => g.toLowerCase().includes(search.value.toLowerCase()))
)

function select(game) {
  emit('update:modelValue', game)
  isOpen.value = false
  search.value = ''
}

function handleClickOutside(e) {
  if (!e.target.closest('.game-select')) isOpen.value = false
}
</script>

<template>
  <div class="game-select" v-click-outside="handleClickOutside">
    <button type="button" class="select-trigger" @click="isOpen = !isOpen">
      <template v-if="modelValue">
        <div class="mini-icon" :style="{ background: getGameColor(modelValue) + '22', color: getGameColor(modelValue) }">
          {{ getGameInitials(modelValue) }}
        </div>
        <span>{{ modelValue }}</span>
      </template>
      <span v-else class="placeholder">Выбери игру</span>
      <span class="chevron" :class="{ open: isOpen }">⌄</span>
    </button>

    <transition name="dropdown-fade">
      <div class="dropdown-panel" v-if="isOpen">
        <input
          v-model="search"
          class="search-input"
          placeholder="Поиск игры..."
          @click.stop
        />
        <div class="options-list">
          <button
            type="button"
            v-for="game in filtered"
            :key="game"
            class="option-item"
            :class="{ selected: modelValue === game }"
            @click="select(game)"
          >
            <div class="mini-icon" :style="{ background: getGameColor(game) + '22', color: getGameColor(game) }">
              {{ getGameInitials(game) }}
            </div>
            <span>{{ game }}</span>
          </button>
          <div v-if="filtered.length === 0" class="no-results">Ничего не найдено</div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.game-select {
  position: relative;
}

.select-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.2s var(--ease);
}

.select-trigger:hover {
  border-color: var(--border-hover);
}

.placeholder {
  color: var(--text-muted);
}

.chevron {
  margin-left: auto;
  color: var(--text-secondary);
  font-size: 12px;
  transition: transform 0.2s var(--ease);
}

.chevron.open {
  transform: rotate(180deg);
}

.mini-icon {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 10px;
  flex-shrink: 0;
}

.dropdown-panel {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
  z-index: 60;
  overflow: hidden;
}

.search-input {
  width: 100%;
  background: var(--bg-primary);
  border: none;
  border-bottom: 1px solid var(--border-color);
  padding: 10px 12px;
  color: var(--text-primary);
  font-size: 13px;
}

.search-input:focus {
  outline: none;
}

.options-list {
  max-height: 260px;
  overflow-y: auto;
  padding: 4px;
}

.option-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  background: none;
  border: none;
  padding: 9px 10px;
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s var(--ease);
}

.option-item:hover {
  background: var(--bg-card-hover);
}

.option-item.selected {
  background: var(--accent-dim);
  color: var(--accent);
}

.no-results {
  padding: 16px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}

.dropdown-fade-enter-active, .dropdown-fade-leave-active {
  transition: opacity 0.15s var(--ease), transform 0.15s var(--ease);
}
.dropdown-fade-enter-from, .dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>