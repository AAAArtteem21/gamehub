<script setup>
import DotaStatsCard from './DotaStatsCard.vue'
const props = defineProps({ account: Object })
const emit = defineEmits(['sync', 'remove'])
const platformLabels = { steam: 'Steam', faceit: 'Faceit', opendota: 'OpenDota', manual: 'Ручной' }
</script>

<template>
  <div class="account-card card">
    <div class="account-header">
      <div>
        <span class="platform-name">{{ platformLabels[account.platform] || account.platform }}</span>
        <span class="verified-badge" v-if="account.verified">✓ верифицирован</span>
        <span class="pending-badge" v-else>ожидает синхронизации</span>
      </div>
      <div class="actions">
        <button class="icon-btn" @click="emit('sync', account.id)" title="Синхронизировать">↻</button>
        <button class="icon-btn danger" @click="emit('remove', account.id)" title="Отключить">✕</button>
      </div>
    </div>

    <div class="last-synced" v-if="account.last_synced_at">
      Обновлено: {{ new Date(account.last_synced_at).toLocaleString('ru-RU') }}
    </div>

    <!-- OpenDota — показываем богатую статистику -->
    <DotaStatsCard
      v-if="account.platform === 'opendota' && account.extra_stats"
      :stats="account.extra_stats"
      :skill-rating="account.skill_rating"
    />

    <!-- Остальные платформы — как раньше, список игр по часам -->
    <div class="snapshots-scroll" v-else-if="account.snapshots?.length">
      <div class="snapshot-row" v-for="s in account.snapshots" :key="s.id">
        <span class="game-name">{{ s.game_name }}</span>
        <span class="playtime">
          {{ Math.round(s.playtime_forever / 60) }}ч всего
          <span v-if="s.today_playtime_minutes !== null" class="today-playtime">
            · +{{ s.today_playtime_minutes }}м сегодня
          </span>
        </span>
      </div>
    </div>
    <div v-else class="empty-hint">Нажми ↻, чтобы подтянуть статистику</div>
  </div>
</template>

<style scoped>
.snapshots-scroll {
  max-height: 320px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-right: 4px;
}

.snapshot-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.snapshot-row:last-child {
  border-bottom: none;
}

.account-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.account-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.platform-name {
  font-weight: 700;
  font-size: 14px;
  margin-right: 10px;
}

.verified-badge {
  font-size: 11px;
  color: var(--success);
}

.pending-badge {
  font-size: 11px;
  color: var(--text-secondary);
}

.actions {
  display: flex;
  gap: 6px;
}

.icon-btn {
  background: var(--bg-card-hover);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
}

.icon-btn:hover {
  color: var(--text-primary);
}

.icon-btn.danger:hover {
  color: var(--danger);
  border-color: var(--danger);
}

.last-synced {
  font-size: 11px;
  color: var(--text-secondary);
}

.snapshots {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.snapshot-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 8px 0;
  border-top: 1px solid var(--border-color);
}

.game-name {
  font-weight: 600;
}

.playtime {
  color: var(--text-secondary);
}

.today-playtime {
  color: var(--accent);
}

.estimated-tag {
  color: var(--text-secondary);
  margin-left: 2px;
}

.empty-hint {
  font-size: 13px;
  color: var(--text-secondary);
  text-align: center;
  padding: 12px 0;
}
</style>