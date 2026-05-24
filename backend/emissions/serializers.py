"""DRF serializers for the emissions app."""

from rest_framework import serializers
from .models import Tenant, DataImport, EmissionRecord


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = "__all__"


class DataImportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataImport
        fields = "__all__"


class EmissionRecordSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source="get_source_type_display", read_only=True)
    scope_display = serializers.CharField(source="get_scope_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = EmissionRecord
        fields = "__all__"


class BulkReviewSerializer(serializers.Serializer):
    """Payload for bulk approve / reject."""
    ids = serializers.ListField(child=serializers.IntegerField())
    action = serializers.ChoiceField(choices=["APPROVED", "REJECTED"])
    reviewer_notes = serializers.CharField(required=False, default="")
