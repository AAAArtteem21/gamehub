<script setup>
import { useToast } from '../../composables/useToast'
const { toasts, dismiss } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-host" aria-live="polite">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="toast"
          :class="t.type"
          @click="dismiss(t.id)"
        >
          <span class="toast-dot" />
          <span class="toast-msg">{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-host {
  position: fixed;
  top: 18px;
  right: 18px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
  max-width: min(360px, calc(100vw - 32px));
}
.toast {
  pointer-events: auto;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
  cursor: pointer;
}
.toast.error { border-color: rgba(248, 113, 113, 0.4); }
.toast.success { border-color: rgba(74, 222, 128, 0.4); }
.toast.info { border-color: rgba(230, 57, 70, 0.4); }
.toast-dot {
  width: 8px; height: 8px; border-radius: 50%; margin-top: 5px; flex-shrink: 0;
}
.toast.error .toast-dot { background: var(--danger); }
.toast.success .toast-dot { background: var(--success); }
.toast.info .toast-dot { background: var(--accent); }
.toast-msg { font-size: 13px; font-weight: 600; line-height: 1.4; color: var(--text-primary); }
.toast-enter-active, .toast-leave-active { transition: all 0.28s var(--ease, ease); }
.toast-enter-from { opacity: 0; transform: translateX(20px); }
.toast-leave-to { opacity: 0; transform: translateX(12px); }
</style>