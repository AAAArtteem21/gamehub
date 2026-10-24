<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import FriendsPanel from './FriendsPanel.vue'
import { friendsApi } from '../../api/friends'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const open = ref(false)
const badge = ref(0)

const show = computed(() => auth.isAuthenticated)

async function refreshBadge() {
  if (!auth.isAuthenticated) {
    badge.value = 0
    return
  }
  try {
    const res = await friendsApi.requests()
    badge.value = (res.data?.incoming || []).length
  } catch {
    /* */
  }
}

function toggle() {
  open.value = !open.value
  if (open.value) refreshBadge()
}

onMounted(() => {
  refreshBadge()
  const poll = setInterval(refreshBadge, 60_000)
  onUnmounted(() => clearInterval(poll))
})
</script>

<template>
  <div v-if="show" class="fb-wrap">
    <button
      type="button"
      class="fb-btn"
      :class="{ open }"
      aria-label="Друзья"
      @click="toggle"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M16 11a4 4 0 1 0-4-4 4 4 0 0 0 4 4Z" />
        <path d="M8 13a4 4 0 1 0-4-4 4 4 0 0 0 4 4Z" />
        <path d="M16 13c-2.7 0-8 1.3-8 4v2h16v-2c0-2.7-5.3-4-8-4Z" />
        <path d="M8 13c-.7 0-1.4.1-2 .2C3.5 13.7 1 15 1 17v2h5" />
      </svg>
      <span v-if="badge > 0" class="fb-badge">{{ badge > 9 ? '9+' : badge }}</span>
    </button>
    <FriendsPanel :open="open" @close="open = false" />
  </div>
</template>

<style scoped>
.fb-wrap {
  position: relative;
}
.fb-btn {
  position: relative;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  background: var(--bg-sunken);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.fb-btn:hover,
.fb-btn.open {
  border-color: var(--accent);
  color: var(--accent);
}
.fb-btn svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.fb-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: var(--accent);
  color: #12100c;
  font-size: 10px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>