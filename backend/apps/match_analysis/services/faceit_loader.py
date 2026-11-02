from __future__ import annotations

def parse_kda(kda: str):
    parts = [p.strip() for p in str(kda or "").split("/")]
    if len(parts) < 3:
        return None, None, None
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None, None, None

def player_from_participants(
    payload: dict,
    faceit_player_id: str | None = None,
    gamehub_user_id: int | None = None,
) -> dict:
    participants = payload.get("participants") or []
    me = None 
    for p in participants:
        if faceit_player_id and str(p.get("player_id")) == str(faceit_player_id):
            me = p
            break
        if gamehub_user_id is not None and p.get("gamehub_user_id") == gamehub_user_id:
            me = p
            break
    if not me:
        raise PermissionError("Игрок не найден в матче Faceit")

    kills, deaths, assists = parse_kda(me.get("kda"))
    team = me.get("team")
    winner = payload.get("winner")
    won = (team == winner) if team and winner else None

    kd = None
    if kills is not None:
        kd = round(kills / deaths, 2) if deaths else float(kills)

    hs = me.get("headshot")
    hs_pct = None
    if hs is not None and kills:
        try:
            hs_pct = round(100.0 * float(hs) / float(kills), 1)
        except (TypeError, ValueError):
            pass

    return {
        "match_id": payload.get("match_id") or payload.get("id"),
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        "kd": kd,
        "headshots": hs,
        "hs_percent": hs_pct,
        "mvps": me.get("mvps"),
        "map": payload.get("map"),
        "won": won,
        "team": team,
        "score": f"{payload.get('faction1_score')}:{payload.get('faction2_score')}",
        "competition": payload.get("competition"),
        "nickname": me.get("nickname"),
        "faceit_player_id": me.get("player_id"),
    }


def load_faceit_match_context(
    *,
    payload: dict,
    faceit_player_id: str | None = None,
    gamehub_user_id: int | None = None,
    recent: list | None = None,
) -> dict:
    match = player_from_participants(
        payload,
        faceit_player_id=faceit_player_id,
        gamehub_user_id=gamehub_user_id
    )
    return {
        "platform": "faceit",
        "game": "cs2",
        "match_id": match.get("match_id"),
        "match": match,
        "recent": recent or [],
        "limits": [
            "статы из Faceit match participants",
            "без демо / таймлайна"
        ],
    }
