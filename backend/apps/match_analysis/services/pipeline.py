from django.utils import timezone

from apps.match_analysis.models import MatchAnalysis

from .ai_analyzer import analyze_dota_snapshot
from .match_loader import load_dota_match_context
from .statistics import _kd, _kda, build_dota_snapshot


def snapshot_from_hint(match_id, steam32, hint: dict) -> dict:
    k = hint.get("kills")
    d = hint.get("deaths")
    a = hint.get("assists")
    return {
        "platform": "opendota",
        "game": "dota2",
        "match_id": match_id,
        "steam32": steam32,
        "match": {
            "match_id": match_id,
            "kills": k,
            "deaths": d,
            "assists": a,
            "gpm": hint.get("gpm"),
            "xpm": hint.get("xpm"),
            "last_hits": hint.get("last_hits"),
            "won": hint.get("won"),
            "kd": _kd(k, d) if k is not None else None,
            "kda": _kda(k, d, a) if k is not None else None,
        },
        "recent": [],
        "limits": ["данные из истории профиля (fallback)"],
    }


def _merge_hint(snapshot: dict, hint: dict) -> dict:
    if not hint:
        return snapshot
    m = snapshot.setdefault("match", {})
    for key, val in hint.items():
        if val is not None and m.get(key) is None:
            m[key] = val
    if m.get("kills") is not None:
        if m.get("kd") is None:
            m["kd"] = _kd(m.get("kills"), m.get("deaths"))
        if m.get("kda") is None:
            m["kda"] = _kda(m.get("kills"), m.get("deaths"), m.get("assists"))
    snapshot["match"] = m
    return snapshot


def run_dota_analysis(analysis: MatchAnalysis, steam32: int, hint=None) -> MatchAnalysis:
    hint = dict(hint or {})
    analysis.status = MatchAnalysis.Status.RUNNING
    analysis.error_message = ""
    analysis.save(update_fields=["status", "error_message"])

    try:
        try:
            ctx = load_dota_match_context(int(steam32), analysis.external_match_id)
            snapshot = build_dota_snapshot(ctx)
        except Exception as load_err:
            if not hint:
                raise load_err
            snapshot = build_dota_snapshot(
                {
                    **snapshot_from_hint(analysis.external_match_id, steam32, hint),
                    "recent": [],
                }
            )
            snapshot = snapshot_from_hint(analysis.external_match_id, steam32, hint)
            from .statistics import summarize_recent

            snapshot["recent_20"] = summarize_recent([])
            snapshot["deltas"] = {}

        snapshot = _merge_hint(snapshot, hint)

        m = snapshot.get("match") or {}
        if m.get("kills") is None and m.get("gpm") is None:
            analysis.status = MatchAnalysis.Status.FAILED
            analysis.error_message = (
                "Нет статистики матча (OpenDota пусто и нет данных из истории)."
            )
            analysis.input_snapshot = snapshot
            analysis.finished_at = timezone.now()
            analysis.save()
            return analysis

        if snapshot.get("recent") is not None and hint:
            try:
                snapshot = build_dota_snapshot(
                    {
                        "platform": "opendota",
                        "game": "dota2",
                        "steam32": steam32,
                        "match_id": analysis.external_match_id,
                        "match": snapshot["match"],
                        "recent": snapshot.get("recent") or [],
                        "limits": snapshot.get("limits") or [],
                    }
                )
            except Exception:
                pass

        report, model_name = analyze_dota_snapshot(snapshot)

        m = snapshot.get("match") or {}
        r20 = snapshot.get("recent_20") or {}
        report["match_stats"] = {
            "kills": m.get("kills"),
            "deaths": m.get("deaths"),
            "assists": m.get("assists"),
            "kd": m.get("kd"),
            "kda": m.get("kda"),
            "gpm": m.get("gpm"),
            "xpm": m.get("xpm"),
            "last_hits": m.get("last_hits"),
            "denies": m.get("denies"),
            "hero_damage": m.get("hero_damage"),
            "tower_damage": m.get("tower_damage"),
            "hero_healing": m.get("hero_healing"),
            "net_worth": m.get("net_worth"),
            "level": m.get("level"),
            "won": m.get("won"),
            "duration_min": m.get("duration_min"),
            "hero_id": m.get("hero_id"),
        }
        report["recent_stats"] = r20
        report["deltas"] = snapshot.get("deltas") or {}

        analysis.input_snapshot = snapshot
        analysis.report_json = report
        analysis.model_name = model_name
        analysis.game = "dota2"
        analysis.status = MatchAnalysis.Status.READY
        analysis.error_message = ""
        analysis.finished_at = timezone.now()
        analysis.save()
    except PermissionError as e:
        analysis.status = MatchAnalysis.Status.FAILED
        analysis.error_message = str(e)
        analysis.finished_at = timezone.now()
        analysis.save()
    except Exception as e:
        analysis.status = MatchAnalysis.Status.FAILED
        analysis.error_message = str(e)[:500]
        analysis.finished_at = timezone.now()
        analysis.save()

    return analysis