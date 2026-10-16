<script setup>
import { computed } from 'vue'
import { clansApi } from '../../api/clans'
import { useToast } from '../../composables/useToast'

const props = defineProps({
  clanId: { type: [Number, String], required: true },
  rows: { type: Array, default: () => [] },
  myRole: { type: String, default: 'member' },
})

const emit = defineEmits(['reload'])
const toast = useToast()

const roleLabels = {
  leader: 'Лидер',
  officer: 'Офицер',
  member: 'Участник',
}

const canModerate = computed(
  () => props.myRole === 'leader' || props.myRole === 'officer'
)

function fmtHours(minutes) {
  const m = Number(minutes) || 0
  if (m <= 0) return '—'
  const h = Math.round((m / 60) * 10) / 10
  return `${h} ч`
}

function fmtDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return '—'
  }
}

async function kickUser(row) {
  if (row.role === 'leader') return
  if (!confirm(`Кикнуть «${row.username}» из клана?`)) return
  try {
    await clansApi.kick(props.clanId, row.user_id)
    toast.success('Участник кикнут')
    emit('reload')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Не удалось кикнуть')
  }
}

async function banUser(row) {
  if (row.role === 'leader') return
  if (
    !confirm(
      `Забанить «${row.username}»? Он не сможет вступить в клан снова, пока бан не снимут.`
    )
  ) {
    return
  }
  try {
    await clansApi.ban(props.clanId, row.user_id, '')
    toast.success('Участник забанен')
    emit('reload')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Не удалось забанить')
  }
}
</script>

<template>
  <div class="dash-wrap">
    <div v-if="!rows?.length" class="empty">
      Пока нет участников или дашборд недоступен.
    </div>

    <div v-else class="table-scroll">
      <table class="dash-table">
        <thead>
          <tr>
            <th>Игрок</th>
            <th>Роль</th>
            <th>2 нед.</th>
            <th>Всего</th>
            <th>Вступил</th>
            <th v-if="canModerate" class="th-actions">Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.user_id"
            :class="{ inactive: row.is_inactive }"
          >
            <td class="name-cell">
              <span class="name">{{ row.username }}</span>
              <span v-if="row.is_inactive" class="inactive-tag">неактивен</span>
            </td>
            <td>
              <span class="role-pill" :class="row.role">
                {{ roleLabels[row.role] || row.role }}
              </span>
            </td>
            <td class="num">{{ fmtHours(row.two_weeks_playtime) }}</td>
            <td class="num">{{ fmtHours(row.total_playtime) }}</td>
            <td class="muted">{{ fmtDate(row.joined_at) }}</td>
            <td v-if="canModerate" class="actions">
              <template v-if="row.role !== 'leader'">
                <button type="button" class="btn-ghost btn-sm" @click="kickUser(row)">
                  Кик
                </button>
                <button type="button" class="btn-ban btn-sm" @click="banUser(row)">
                  Бан
                </button>
              </template>
              <span v-else class="muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.dash-wrap {
  width: 100%;
}
.empty {
  padding: 28px 16px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}
.table-scroll {
  overflow-x: auto;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}
.dash-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 520px;
}
.dash-table th {
  text-align: left;
  padding: 10px 14px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-sunken);
}
.dash-table td {
  padding: 11px 14px;
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;
}
.dash-table tr:last-child td {
  border-bottom: none;
}
.dash-table tbody tr:hover {
  background: var(--bg-card-hover);
}
.dash-table tbody tr.inactive {
  opacity: 0.72;
}
.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.name {
  font-weight: 600;
  color: var(--text-primary);
}
.inactive-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--bg-sunken);
  color: var(--text-muted);
}
.role-pill {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--bg-sunken);
  color: var(--text-secondary);
}
.role-pill.leader {
  background: var(--accent-dim);
  color: var(--accent);
}
.role-pill.officer {
  background: var(--accent-2-dim, rgba(255, 255, 255, 0.08));
  color: var(--accent-2, #fff);
}
.num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.muted {
  color: var(--text-muted);
  font-size: 12px;
}
.th-actions,
.actions {
  white-space: nowrap;
}
.actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.btn-sm {
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  border-radius: 6px;
  line-height: 1.2;
}
.btn-ghost {
  background: var(--bg-sunken);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}
.btn-ghost:hover {
  border-color: var(--border-hover);
  color: var(--text-primary);
}
.btn-ban {
  background: transparent;
  border: 1px solid rgba(230, 57, 70, 0.4);
  color: var(--danger);
}
.btn-ban:hover {
  background: rgba(230, 57, 70, 0.12);
}
</style>