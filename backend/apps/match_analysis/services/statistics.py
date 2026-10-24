"""Детерминированная аналитика Dota — без LLM."""

from __future__ import annotations

def _kd(k, d) -> float:
    k = k or 0
    d = d or 0
    return round(k / d, 2) if d else float(k)


def _kda(k, d, a) -> float:
    k, d, a = k or 0, d or 0, a or 0
    return  round((k + a) / d, 2) if d else float(k + a)


def summarize_recent(recent: list[dict]) -> dict:
    if not recent:
        return {
            "matches": 0,
            "wins": 0,
            "winrate": 0,
            "avg_kills": 0,
            "avg_assists": 0,
            "avg_kd": 0,
            "avg_kda": 0,
            "avg_gpm": 0,
            "avg_xpm": 0,
            "form": [],
        }

    n = len(recent)
    wins = 0
    sk = sd = sa = sg = sx = 0
    form = []

    for m in recent:
        is_rad = (m.get("player_slot") or 0) < 128
        rw = bool(m.get("radiant_win"))
        won = rw if is_rad else not rw
        if won:
            wins += 1
        form.append("w" if won else "L")
        sk += m.get("kills") or 0
        sd += m.get("deaths") or 0
        sa += m.get("assists") or 0
        sg += m.get("gold_per_min") or 0
        sx += m.get("xp_per_min") or 0

    avg_k = round(sk / n, 1)
    avg_d = round(sd / n, 1)
    avg_a = round(sa / n, 1)

    return {
        "matches": n,
        "wins": wins,
        "winrate": round(100 * wins / n, 1),
        "avg_kills": avg_k,
        "avg_deaths": avg_d,
        "avg_assists": avg_a,
        "avg_kd": _kd(avg_k, avg_d),
        "avg_kda": _kda(avg_k, avg_d, avg_a),
        "avg_gpm": round(sg / n),
        "avg_xpm": round(sx / n),
        "form": form[:10],
    }


def build_dota_snapshot(ctx: dict) -> dict:
    m = ctx["match"]
    recent_sum = summarize_recent(ctx.get("recent") or [])

    k, d, a = m.get("kills") or 0, m.get("deaths") or 0, m.get("assits") or 0
    kd = _kd(k, d)
    kda = _kda(k, d, a)

    deltas = {}
    if recent_sum["matches"]:
        deltas = {
            "kd_vs_avg": round(kd - recent_sum["avg_kd"], 2),
            "kills_vs_avg": round(k - recent_sum["avg_kills"], 1),
            "deaths_vs_avg": round(d - recent_sum["avg_deaths"], 1),
            "gpm_vs_avg": (m.get("gpm") or 0) - recent_sum["avg_gpm"],
            "xpm_vs_avg": (m.get("xpm") or 0) - recent_sum["avg_xpm"],
        }

    return {
        "platform": "opendota",
        "game": "dota2",
        "match_id": ctx["match_id"],
        "steam32": ctx["steam32"],
        "match": {
            **m,
            "kd": kd,
            "kda": kda,
            "duration_min": round((m.get("duration") or 0) / 60, 1),
        },
        "recent_20": recent_sum,
        "deltas": deltas,
        "limits": ctx.get("limits") or [],
    }
