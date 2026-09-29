<!-- src/components/lfg/GameIcon.vue — ПОЛНАЯ замена -->
<script setup>
import { getGameColor, getGenre } from '../../constants/games'

const props = defineProps({ game: String, size: { type: Number, default: 44 } })
</script>

<template>
  <div class="game-icon" :style="{ width: size + 'px', height: size + 'px', background: getGameColor(game || '') + '1f', color: getGameColor(game || '') }">
    <svg v-if="getGenre(game) === 'shooter'" viewBox="0 0 24 24" fill="none" :width="size*0.55" :height="size*0.55">
      <circle cx="12" cy="12" r="7" stroke="currentColor" stroke-width="1.6"/>
      <path d="M12 2v4M12 18v4M2 12h4M18 12h4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
    </svg>
    <svg v-else-if="getGenre(game) === 'moba'" viewBox="0 0 24 24" fill="none" :width="size*0.55" :height="size*0.55">
      <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
      <path d="M9 12l2 2 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    <svg v-else-if="getGenre(game) === 'openworld'" viewBox="0 0 24 24" fill="none" :width="size*0.55" :height="size*0.55">
      <path d="M12 2l2.4 6.8L21 11l-6.6 2.2L12 20l-2.4-6.8L3 11l6.6-2.2L12 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
    </svg>
    <svg v-else-if="getGenre(game) === 'survival'" viewBox="0 0 24 24" fill="none" :width="size*0.55" :height="size*0.55">
      <path d="M12 3c2 3 5 5.5 5 9a5 5 0 01-10 0c0-1.5.6-2.6 1.3-3.6.3 1 1 1.6 1 1.6-.4-3 1-4.5 2.7-7z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
    </svg>
    <svg v-else-if="getGenre(game) === 'horror'" viewBox="0 0 24 24" fill="none" :width="size*0.55" :height="size*0.55">
      <path d="M12 3a7 7 0 00-7 7v6a2 2 0 002 2h1v-3M12 3a7 7 0 017 7v6a2 2 0 01-2 2h-1v-3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
      <circle cx="9.5" cy="11" r="1" fill="currentColor"/>
      <circle cx="14.5" cy="11" r="1" fill="currentColor"/>
    </svg>
    <svg v-else-if="getGenre(game) === 'sim'" viewBox="0 0 24 24" fill="none" :width="size*0.55" :height="size*0.55">
      <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.6"/>
      <path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
    </svg>
    <svg v-else-if="getGenre(game) === 'racing'" viewBox="0 0 24 24" fill="none" :width="size*0.55" :height="size*0.55">
      <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.6"/>
      <circle cx="12" cy="12" r="2.3" stroke="currentColor" stroke-width="1.6"/>
      <path d="M12 4v3.5M12 16.5V20M4 12h3.5M16.5 12H20" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
    </svg>
    <svg v-else-if="getGenre(game) === 'rpg'" viewBox="0 0 24 24" fill="none" :width="size*0.55" :height="size*0.55">
      <path d="M6.5 17.5L17 7M17 7L15 4L20 3L19 8L17 7Z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M4 20L6.5 17.5L8 19L5.5 21.5L4 20Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
    </svg>
    <svg v-else-if="getGenre(game) === 'sports'" viewBox="0 0 24 24" fill="none" :width="size*0.55" :height="size*0.55">
      <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.6"/>
      <path d="M12 4c2 2 3 5 3 8s-1 6-3 8M12 4c-2 2-3 5-3 8s1 6 3 8M4 12h16" stroke="currentColor" stroke-width="1.4"/>
    </svg>
    <svg v-else-if="getGenre(game) === 'life'" viewBox="0 0 24 24" fill="none" :width="size*0.55" :height="size*0.55">
      <path d="M4 11L12 4l8 7M6 10v9a1 1 0 001 1h10a1 1 0 001-1v-9" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
    </svg>
    <svg v-else viewBox="0 0 24 24" fill="none" :width="size*0.55" :height="size*0.55">
      <rect x="3" y="8" width="18" height="9" rx="4" stroke="currentColor" stroke-width="1.6"/>
      <path d="M8 11v3M6.5 12.5h3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
      <circle cx="16" cy="11.5" r="0.9" fill="currentColor"/>
      <circle cx="18" cy="13.5" r="0.9" fill="currentColor"/>
    </svg>
  </div>
</template>

<style scoped>
.game-icon {
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
</style>