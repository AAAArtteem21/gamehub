from __future__ import annotations

from .faceit_loader import parse_kda

def _kd(k, d):
    if k is None:
        return None
    return round(k / d, 2) if d else float(k)

def summarize_faceit_recent(recent: list) -> dict:
    """
    recent: элементы match_history или [{won, kills, deaths, assists, kda}, ...]
    """
    if not recent:
        return {
            "matches": 0,
            "wins": 0,
            "winrate": 0,
            "form": [],
            "avg_kills": None,
            "avg_deaths": None,
            "avg_assits": None,
            "avg_kd": None
        }

    kills_l, deaths_l, assits_l = [], [], []
    form = []
    wins = 0

    for m in recent[:20]:
        k, d ,a = m.get("kills"), m.get("deaths"), m.get("assits")
        if k is not None and m.get("kda"):
            k, d, a = parse_kda(m.get("kda"))
        if k is not None:
            kills_l.append(k)
        if d is not None:
            deaths_l.append(d)
        if a is not None:
            assits_l.append(a)

        won = m.get("won")
        if won is True:
            wins += 1
            form.append("W")
        elif won is False:
            form.append("L")

    n = len(recent[:20])
    avg = lambda xs: round(sum(xs) / len(xs), 2) if xs else None

    return {
        "matches": n,
        "wins": wins,
        "winrate": round(100.0 * wins / n , 1) if n else 0,
        "form": form[-10:],
        "avg_kills": avg(kills_l),
        "avg_deaths": avg(deaths_l),
        "avg_assits": avg(assits_l),
        "avg_kd": avg([_kd(k, d) for k, d in zip(kills_l, deaths_l)]) if kills_l else None,
    }

def build_faceit_snapshots(ctx: dict) -> dict:
    m = dict(ctx.get("match") or {})
    recent = ctx.get("recent") or []
    r20 = summarize_faceit_recent(recent)

    def delta(val, avg):
        if val is None or avg is None:
            return None
        return round(float(val)) - float((avg), 2)

    deltas = {
        "kd_vs_avg": delta(m.get("kd"), r20.get("avg_kd")),
        "kills_vs_avg": delta(m.get("kills"), r20.get("avg_kills")),
        "deaths_vs_avg": delta(m.get("deaths"), r20.get("avg_deaths")),
    }

    return {
        "platform": "faceit",
        "game": "cs2",
        "match_id": ctx.get("match_id") or m.get("match_id"),
        "match": m,
        "recent": recent,
        "recent_20": r20,
        "deltas": deltas,
        "limits": ctx.get("limits") or [],
    }