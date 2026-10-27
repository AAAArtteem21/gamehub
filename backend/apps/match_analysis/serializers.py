from rest_framework import serializers
from .models import MatchAnalysis

class CreateDotaAnalystSerializer(serializers.Serializer):
    match_id = serializers.CharField(max_length=32)
    kills = serializers.IntegerField(required=False, allow_null=True)
    deaths = serializers.IntegerField(required=False, allow_null=True)
    assists = serializers.IntegerField(required=False, allow_null=True)
    gpm = serializers.IntegerField(required=False, allow_null=True)
    xpm = serializers.IntegerField(required=False, allow_null=True)
    last_hits = serializers.IntegerField(required=False, allow_null=True)
    won = serializers.BooleanField(required=False, allow_null=True)


class MatchAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchAnalysis
        fields = [
            "id",
            "platform",
            "game",
            "external_match_id",
            "status",
            "input_snapshot",
            "report_json",
            "model_name",
            "error_message",
            "created_at",
            "finished_at"
        ]
        read_only_fields = fields