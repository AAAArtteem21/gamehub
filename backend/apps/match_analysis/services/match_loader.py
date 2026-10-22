from __future__ import annotations

import logging
from typing import Any 

import requests
from django.conf import settings

logger = logging.getLogger(__name__)



OPENDOTA = getattr(settings, "OPENDOTA_API_URL", "https://api.opendota.com/api").rstrip("/")
TIMEOUT = 20


def _get(path: str, params: dict | None = None):
    path = "/" + str(path).lstrip("/")
    url = f"{OPENDOTA}{path}"
    r = requests.get(url, params=params or {}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def fetch_player_recent(steam32: int, limit: int = 20) -> list:
    data = _get(f"/players/{steam32}/recentMatches")
    if not isinstance(data, list):
        return []
    return data[:limit]


def fetch_match(match_id: int | str) -> dict:
    return _get(f"/matches/{int(match_id)}")

def find_player_slot(match: dict, steam32: int) -> dict | None:
    for p in match.get("players") or []:
        if p.get("account_id") == steam32:
            return p 
    return None

def load_dota_match_context(steam32: int, match_id: int | str) -> dict:
    """ берет этот матч+ recent20 для формы"""
    match_id = int(match_id)
    match = fetch_match(match_id)
    me = find_player_slot(match, steam32)
    if not me:
        raise PermissionError("в этом матче нету этого игрока")

    radiant_win = bool(match.get("radiant_win"))
    is_radiant = me.get("player_slot", 0) < 120
    won = radiant_win if is_radiant else not radiant_win

    recent = fetch_player_recent(steam32, limit=20)

    return {
        "platform": "opendota",
        "game": "dota2",
        "steam32": steam32,
        "match_id": match_id,
        "match": {
            "match_id": match_id,
            "start_time": match.get("start_time"),
            "duration": match.get("duration"),
            "lobby_type": match.get("lobby_type"),
            "game_mode": match.get("game_mode"),
            "hero_id": me.get("hero_id"),
            "kills": me.get("kills"),
            "deaths": me.get("deaths"),
            "assists": me.get("assists"),
            "last_hits": me.get("last_hits"),
            "denies": me.get("denies"),
            "gpm": me.get("gold_per_min"),
            "xpm": me.get("xp_per_min"),
            "hero_damage": me.get("hero_damage"),
            "tower_damage": me.get("tower_damage"),
            "hero_healing": me.get("hero_healing"),
            "net_worth": me.get("net_worth") or me.get("total_gold"),
            "level": me.get("level"),
            "won": won,
            "is_radiant": is_radiant,
            "party_size": me.get("party_size"),
        },
        "recent": recent,
        "limits": [
            "нет полного реплея / timeline",
            "нет анализа vision и item timings (если не в match details)",
            "recentMatches — краткая лента, не полный parse",
        ],
    }

