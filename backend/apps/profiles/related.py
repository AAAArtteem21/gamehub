from __future__ import annotations
from urllib.parse import quote


def steam32_to_64(account_id) -> str:
    try:
        return str(int(account_id) + 76561197960265728)
    except (TypeError, ValueError):
        return ""


def steam64_to_32(steam_id) -> str:
    s = str(steam_id or "").strip()
    if s.startswith("7656119"):
        try:
            return str(int(s) & 0xFFFFFFFF)
        except ValueError:
            return s
    return s


def related_games_for_steam32(steam32: str, *, current: str = "") -> list[dict]:
    raw = str(steam32 or "").strip()
    if not raw:
        return []
    # всегда Steam32 для dota/deadlock
    sid = steam64_to_32(raw) if raw.startswith("7656119") else raw
    try:
        sid = str(int(sid))
    except (TypeError, ValueError):
        return []

    cur = (current or "").lower()
    if cur in ("opendota", "dota"):
        cur = "dota2"

    candidates = [
        {
            "game": "dota2",
            "label": "Dota 2",
            "platform": "opendota",
            "external_id": sid,
            "path": f"/players/guest/dota2/{sid}",
        },
        {
            "game": "deadlock",
            "label": "Deadlock",
            "platform": "deadlock",
            "external_id": sid,
            "path": f"/players/guest/deadlock/{sid}",
        },
        # Faceit: без steam64 в path — отдельный lookup на бэке по steam, иначе 404
        # пока не ведём на faceit из steam32, пока guest не резолвит steam→ник
    ]
    return [c for c in candidates if c["game"] != cur]


def related_games_for_riot(riot_id: str, *, current: str = "") -> list[dict]:
    rid = (riot_id or "").strip()
    if not rid or "#" not in rid:
        return []
    cur = (current or "").lower()
    enc = quote(rid, safe="")
    candidates = [
        {
            "game": "valorant",
            "label": "Valorant",
            "platform": "valorant",
            "external_id": rid,
            "path": f"/players/guest/valorant/{enc}",
        },
        {
            "game": "lol",
            "label": "League of Legends",
            "platform": "lol",
            "external_id": rid,
            "path": f"/players/guest/lol/{enc}",
        },
    ]
    return [c for c in candidates if c["game"] != cur]