<script setup>
import { getGameColor, getGameInitials } from '../../constants/games'

const props = defineProps({ game: String })
</script>

<template>
  <div class="game-icon" :style="{ background: getGameColor(game || '') + '22', color: getGameColor(game || '') }">
    {{ getGameInitials(game || '??') }}
  </div>
</template>

<style scoped>
.game-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 13px;
  flex-shrink: 0;
}
</style>