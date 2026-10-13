<!-- src/components/clans/ClanDashboardTable.vue -->
<script setup>
import { ref } from 'vue'
import api from '../../api/axios'

const props = defineProps({ entries: Array, clanId: Number, isLeader: Boolean })
const emit = defineEmits(['updated'])

const busyUserId = ref(null)

function formatHours(min) {
  if (!min) return '0ч'
  const h = min / 60
  return h >= 10 ? `${Math.round(h)}ч` : `${(Math.round(h * 10) / 10).toFixed(1)}ч`
}

async function changeRole(userId, role) {
  busyUserId.value = userId
  try {
    await api.post(`clans/${props.clanId}/change_role/`, { user_id: userId, role })
    emit('updated')
  } catch (e) {
    alert(e.response?.data?.detail || 'Не удалось изменить роль')
  } finally {
    busyUserId.value = null
  }
}

async function kick(userId, username) {
  if (!confirm(`Исключить ${username} из клана?`)) return
  busyUserId.value = userId
  try {
    await api.post(`clans/${props.clanId}/kick/`, { user_id: userId })
    emit('updated')
  } catch (e) {
    alert(e.response?.data?.detail || 'Не удалось исключить участника')
  } finally {
    busyUserId.value = null
  }
}
</script>

<template>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Участник</th>
          <th>Роль</th>
          <th>За 2 недели</th>
          <th>Всего</th>
          <th>Активность</th>
          <th v-if="isLeader">Управление</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in entries" :key="e.user_id" :class="{ inactive: e.is_inactive }">
          <td>
            <RouterLink :to="`/players/${e.user_id}`" class="username-link">{{ e.username }}</RouterLink>
          </td>
          <td><span class="role-badge" :class="e.role">{{ e.role }}</span></td>
          <td class="num">{{ formatHours(e.two_weeks_playtime) }}</td>
          <td class="num">{{ formatHours(e.total_playtime) }}</td>
          <td>
            <span v-if="e.is_inactive" class="inactive-tag">неактивен</span>
            <span v-else class="active-tag">● активен</span>
          </td>
          <td v-if="isLeader">
            <div class="controls" v-if="e.role !== 'leader'">
              <select
                class="role-select"
                :value="e.role"
                @change="changeRole(e.user_id, $event.target.value)"
                :disabled="busyUserId === e.user_id"
              >
                <option value="member">Участник</option>
                <option value="officer">Офицер</option>
                <option value="leader">Передать лидерство</option>
              </select>
              <button class="kick-btn" @click="kick(e.user_id, e.username)" :disabled="busyUserId === e.user_id">
                Кикнуть
              </button>
            </div>
            <span v-else class="you-tag">Это ты</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 10px 12px; color: var(--text-secondary); font-weight: 600; border-bottom: 1px solid var(--border-color); font-size: 12px; text-transform: uppercase; letter-spacing: 0.3px; }
td { padding: 12px; border-bottom: 1px solid var(--border-color); }
tr.inactive { opacity: 0.5; }
.num { font-family: var(--font-mono); font-variant-numeric: tabular-nums; font-weight: 600; }

.username-link { font-weight: 600; color: var(--text-primary); text-decoration: none; }
.username-link:hover { color: var(--accent); text-decoration: underline; }

.role-badge { font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 20px; text-transform: uppercase; }
.role-badge.leader { background: var(--accent-dim); color: var(--accent); }
.role-badge.officer { background: rgba(74, 222, 128, 0.12); color: var(--success); }
.role-badge.member { background: var(--bg-card-hover); color: var(--text-secondary); }

.active-tag { color: var(--success); font-size: 12px; }
.inactive-tag { color: var(--text-secondary); font-size: 12px; }

.controls { display: flex; gap: 6px; align-items: center; }
.role-select {
  background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-primary);
  font-size: 11px; padding: 5px 8px; border-radius: 6px;
}
.kick-btn {
  background: rgba(248, 113, 113, 0.1); border: 1px solid var(--danger); color: var(--danger);
  font-size: 11px; padding: 5px 10px; border-radius: 6px; cursor: pointer; white-space: nowrap;
}
.kick-btn:hover { background: rgba(248, 113, 113, 0.2); }
.you-tag { font-size: 11px; color: var(--text-muted); font-style: italic; }
</style>