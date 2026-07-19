<script setup>
defineProps({ entries: Array })

function formatMinutes(min) {
  if (!min) return '0м'
  const h = Math.floor(min / 60)
  const m = min % 60
  return h > 0 ? `${h}ч ${m}м` : `${m}м`
}
</script>

<template>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Участник</th>
          <th>Роль</th>
          <th>Сегодня</th>
          <th>За неделю</th>
          <th>За месяц</th>
          <th>Активность</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in entries" :key="e.user_id" :class="{ inactive: e.is_inactive }">
          <td class="username">{{ e.username }}</td>
          <td><span class="role-badge" :class="e.role">{{ e.role }}</span></td>
          <td>{{ formatMinutes(e.today_playtime) }}</td>
          <td>{{ formatMinutes(e.week_playtime) }}</td>
          <td>{{ formatMinutes(e.month_playtime) }}</td>
          <td>
            <span v-if="e.is_inactive" class="inactive-tag">неактивен</span>
            <span v-else class="active-tag">● активен</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th {
  text-align: left;
  padding: 10px 12px;
  color: var(--text-secondary);
  font-weight: 600;
  border-bottom: 1px solid var(--border-color);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

td {
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
}

tr.inactive {
  opacity: 0.5;
}

.username {
  font-weight: 600;
}

.role-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 20px;
  text-transform: uppercase;
}

.role-badge.leader {
  background: var(--accent-dim);
  color: var(--accent);
}

.role-badge.officer {
  background: rgba(74, 222, 128, 0.12);
  color: var(--success);
}

.role-badge.member {
  background: var(--bg-card-hover);
  color: var(--text-secondary);
}

.active-tag {
  color: var(--success);
  font-size: 12px;
}

.inactive-tag {
  color: var(--text-secondary);
  font-size: 12px;
}
</style>