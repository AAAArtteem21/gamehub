<script setup>
const props = defineProps({ clan: Object, size: { type: Number, default: 48 } })

const PALETTE = ["#E63946", "#3A9BDC", "#4ADE80", "#A855F7", "#F0A020", "#EC4899", "#14B8A6"]

function colorFor(name) {
  let hash = 0
  for (let i = 0; i < (name || "").length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return PALETTE[Math.abs(hash) % PALETTE.length]
}

function initials(name) {
  const clean = (name || "??").trim()
  const parts = clean.split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return clean.slice(0, 2).toUpperCase()
}

function logoUrl() {
  const l = props.clan?.logo
  if (!l) return null
  if (typeof l === "string") return l
  return l.url || null
}
</script>

<template>
  <div
    class="clan-icon"
    :style="{
      width: size + 'px',
      height: size + 'px',
      backgroundImage: logoUrl() ? `url(${logoUrl()})` : 'none',
      background: logoUrl()
        ? undefined
        : `linear-gradient(135deg, ${colorFor(clan.name)}, ${colorFor(clan.name)}99)`,
    }"
  >
    <span v-if="!logoSrc" :style="{ fontSize: size * 0.36 + 'px' }">{{ initials(clan?.name) }}</span>
  </div>
</template>

<style scoped>
.clan-icon {
  border-radius: 12px;
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 800;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
</style>