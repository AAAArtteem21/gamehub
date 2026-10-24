from django.utils import timezone
from apps.match_analysis.models import MatchAnalysis
from .match_loader import load_dota_match_context
from .statistics import build_dota_snapshot
from .ai_analyzer import analyze_dota_snapshot


def run_dota_analysis(analysis: MatchAnalysis, steam32: int) -> MatchAnalysis:
    analysis.status = MatchAnalysis.Status.RUNNING
    analysis.error_message = ""
    analysis.save(update_fields=["status", "error_message"])

    try:
        ctx = load_dota_match_context(int(steam32), analysis.external_match_id)
        snapshot = build_dota_snapshot(ctx)
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