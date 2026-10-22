from rest_framework import serializers
from .models import MatchAnalysis

class CreateDotaAnalystSerializer(serializers.Serializer):
    match_id = serializers.CharField(max_length=32)


class MatchAnalysisSerializer(serializers.ModelSerializer):
    input_snapshots = serializers.JSONField(source="input_snapshot", read_only=True)
    class Meta:
        model = MatchAnalysis
        fields = [
            "id",
            "platform",
            "game",
            "external_match_id",
            "status",
            "input_snapshots",
            "report_json",
            "model_name",
            "error_message",
            "created_at",
            "finished_at"
        ]
        read_only_fields = fields