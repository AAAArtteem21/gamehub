from django.utils import timezone
from apps.match_analysis.models import MatchAnalysis
from .match_loader import load_dota_match_context
from .statistics import build_dota_snapshots
from .ai_analyzer import analyze_dota_snapshots


def run_dota_analysis(analysis: MatchAnalysis, steam32: int) -> MatchAnalysis:
    analysis.status = MatchAnalysis.Status.RUNNING
    analysis.save(update_fields=["status"])

    try:
        ctx = load_dota_match_context(steam32, analysis.external_match_id)
        snapshot = build_dota_snapshots(ctx)
        report, model_name = analyze_dota_snapshots(snapshot)

        analysis.input_snapshot = snapshot
        analysis.report_json = report
        analysis.model_name = model_name
        analysis.status = MatchAnalysis.Status.READY
        analysis.error_message = ""
        analysis.finished_at = timezone.now()
        analysis.game = "dota2"
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
