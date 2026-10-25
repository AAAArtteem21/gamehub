from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MatchAnalysis
from .serializers import MatchAnalysisSerializer,CreateDotaAnalystSerializer
from .services.pipeline import run_dota_analysis

def resolve_steam32(user) -> int | None:
    """
    UserProfile.steam_id может быть steam64 или steam32.
    OpenDota account_id = steam32.
    """
    profile = getattr(user, "profile", None)
    raw = None
    if profile is not None:
        raw = (profile.steam_id or "").strip()

    if raw:
        try:
            n = int(raw)
            if n >= 76561197960265728:
                return n - 76561197960265728
            if n > 0:
                return n
        except ValueError:
            pass

    try:
        social = user.social_auth.filter(provider="steam").first()
        if social and social.uid:
            steam64 = int(social.uid)
            return steam64 - 76561197960265728
    except Exception:
        pass

    return None

class CreateDotaAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            ser = CreateDotaAnalystSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            match_id = str(ser.validated_data["match_id"]).strip()

            hint = {
                k: ser.validated_data[k]
                for k in ("kills", "deaths", "assists", "gpm", "xpm", "last_hits", "won")
                if k in ser.validated_data and ser.validated_data.get(k) is not None
            }

            steam32 = resolve_steam32(request.user)
            if not steam32:
                return Response(
                    {"detail": "Не привязан Steam / steam32"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            analysis, created = MatchAnalysis.objects.get_or_create(
                user=request.user,
                platform=MatchAnalysis.Platform.OPENDOTA,
                external_match_id=match_id,
                defaults={"game": "dota2", "status": MatchAnalysis.Status.PENDING},
            )

            snap = analysis.input_snapshot or {}
            match = snap.get("match") or {}
            report = analysis.report_json or {}
            stats = report.get("match_stats") or {}

            has_stats = analysis.status == MatchAnalysis.Status.READY and (
                match.get("kills") is not None
                or stats.get("kills") is not None
                or match.get("gpm") is not None
                or stats.get("gpm") is not None
            )

            if not created and has_stats:
                return Response(MatchAnalysisSerializer(analysis).data)

            analysis.status = MatchAnalysis.Status.PENDING
            analysis.input_snapshot = {}
            analysis.report_json = {}
            analysis.error_message = ""
            analysis.model_name = ""
            analysis.finished_at = None
            analysis.save(
                update_fields=[
                    "status",
                    "input_snapshot",
                    "report_json",
                    "error_message",
                    "model_name",
                    "finished_at",
                ]
            )

            analysis = run_dota_analysis(analysis, steam32, hint=hint)

            if analysis.status == MatchAnalysis.Status.FAILED:
                return Response(
                    MatchAnalysisSerializer(analysis).data,
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(MatchAnalysisSerializer(analysis).data)

        except Exception as e:
            import traceback

            traceback.print_exc()
            return Response(
                {"detail": str(e), "type": type(e).__name__},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class MatchAnalysisDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self,request,pk):
        try:
            a = MatchAnalysis.objects.get(pk=pk, user=request.user)
        except MatchAnalysis.DoesNotExist:
            return Response({"detail": "Не найдено"}, status=404)
        return Response(MatchAnalysisSerializer(a).data)


class MyDotaAnalysesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = MatchAnalysis.objects.filter(
            user=request.user, platform=MatchAnalysis.Platform.OPENDOTA
        )[:30]
        return Response(MatchAnalysisSerializer(qs, many=True).data)
