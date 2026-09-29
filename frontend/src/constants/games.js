import cs2Icon from '../assets/icons/games/cs2.svg'
import dota2Icon from '../assets/icons/games/dota2.svg'
import valorantIcon from '../assets/icons/games/valorant.svg'
import pubgIcon from '../assets/icons/games/pubg.svg'



export const GAME_ICONS = {
  "Counter-Strike 2": cs2Icon,
  "Dota 2": dota2Icon,
  "Valorant": valorantIcon,
  "PUBG: BATTLEGROUNDS": pubgIcon,
}

export const GAMES = [
  "Counter-Strike 2", "Dota 2", "PUBG: BATTLEGROUNDS", "Marvel Rivals",
  "Apex Legends", "Rust", "Grand Theft Auto V", "Delta Force",
  "Dead by Daylight", "Team Fortress 2", "Tom Clancy's Rainbow Six Siege",
  "Overwatch", "Destiny 2", "PAYDAY 2", "Red Dead Redemption 2",
  "Forza Horizon 6", "ARK: Survival Ascended", "Left 4 Dead 2",
  "Battlefield 6", "Project Zomboid", "Euro Truck Simulator 2",
  "Escape from Tarkov", "Call of Duty", "ARK: Survival Evolved",
  "The Sims 4", "HELLDIVERS 2", "ARC Raiders", "Diablo IV",
  "Black Desert", "Monster Hunter: World", "ELDEN RING NIGHTREIGN",
  "R.E.P.O.", "Farming Simulator 25", "Unturned", "Wuthering Waves",
  "Monster Hunter Wilds", "PEAK", "THE FINALS", "Squad",
  "Rocket League", "The Elder Scrolls Online",
]

export const GENRE_BY_GAME = {
  "Counter-Strike 2": "shooter", "Valorant": "shooter", "PUBG: BATTLEGROUNDS": "shooter",
  "Apex Legends": "shooter", "Tom Clancy's Rainbow Six Siege": "shooter", "Battlefield 6": "shooter",
  "Call of Duty": "shooter", "Escape from Tarkov": "shooter", "THE FINALS": "shooter",
  "Delta Force": "shooter", "Squad": "shooter", "HELLDIVERS 2": "shooter", "ARC Raiders": "shooter",
  "Team Fortress 2": "shooter", "Overwatch": "shooter", "PAYDAY 2": "shooter",

  "Dota 2": "moba",

  "Grand Theft Auto V": "openworld", "Red Dead Redemption 2": "openworld",

  "Rust": "survival", "ARK: Survival Ascended": "survival", "ARK: Survival Evolved": "survival",
  "Project Zomboid": "survival", "The Sims 4": "life",

  "Dead by Daylight": "horror",

  "Euro Truck Simulator 2": "sim", "Farming Simulator 25": "sim", "Forza Horizon 6": "racing",

  "Diablo IV": "rpg", "The Elder Scrolls Online": "rpg", "Monster Hunter: World": "rpg",
  "Monster Hunter Wilds": "rpg", "Black Desert": "rpg", "ELDEN RING NIGHTREIGN": "rpg",
  "Marvel Rivals": "shooter", "Destiny 2": "shooter",

  "Rocket League": "sports",
}

const PALETTE = ["#E63946", "#F0A020", "#3A9BDC", "#4ADE80", "#A855F7", "#EC4899", "#14B8A6", "#F97316"]

export function getGameColor(name) {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return PALETTE[Math.abs(hash) % PALETTE.length]
}

export function getGameInitials(name) {
  const clean = name.replace(/[^\wА-Яа-я\s]/g, '').trim()
  const parts = clean.split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return clean.slice(0, 2).toUpperCase()
}

export function getGenre(game) {
  return GENRE_BY_GAME[game] || "generic"
}