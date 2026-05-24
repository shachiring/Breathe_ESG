"""
API views for the emissions app.
"""

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
# from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Tenant, DataImport, EmissionRecord
from .serializers import (
    TenantSerializer,
    DataImportSerializer,
    EmissionRecordSerializer,
    BulkReviewSerializer,
)
from .ingestion.sap import parse_sap_csv
from .ingestion.utility import parse_utility_csv
from .ingestion.travel import parse_travel_json


# ---------------------------------------------------------------------------
# Tenant CRUD
# ---------------------------------------------------------------------------
class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer


# ---------------------------------------------------------------------------
# DataImport list / detail
# ---------------------------------------------------------------------------
class DataImportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DataImportSerializer

    def get_queryset(self):
        qs = DataImport.objects.all()
        tenant = self.request.query_params.get("tenant")
        if tenant:
            qs = qs.filter(tenant_id=tenant)
        return qs


# ---------------------------------------------------------------------------
# EmissionRecord list / detail + review actions
# ---------------------------------------------------------------------------
class EmissionRecordViewSet(viewsets.ModelViewSet):
    serializer_class = EmissionRecordSerializer

    def get_queryset(self):
        qs = EmissionRecord.objects.select_related("data_import", "tenant").all()
        # Filters
        tenant = self.request.query_params.get("tenant")
        source = self.request.query_params.get("source_type")
        scope = self.request.query_params.get("scope")
        review_status = self.request.query_params.get("status")
        import_id = self.request.query_params.get("import_id")

        if tenant:
            qs = qs.filter(tenant_id=tenant)
        if source:
            qs = qs.filter(source_type=source)
        if scope:
            qs = qs.filter(scope=scope)
        if review_status:
            qs = qs.filter(status=review_status)
        if import_id:
            qs = qs.filter(data_import_id=import_id)
        return qs

    @action(detail=False, methods=["post"])
    def bulk_review(self, request):
        """Approve or reject multiple records at once."""
        ser = BulkReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        ids = ser.validated_data["ids"]
        new_status = ser.validated_data["action"]
        notes = ser.validated_data.get("reviewer_notes", "")

        updated = EmissionRecord.objects.filter(
            id__in=ids,
            status__in=["PENDING", "FLAGGED"],
        ).update(
            status=new_status,
            reviewer_notes=notes,
            reviewed_at=timezone.now(),
        )

        return Response({"updated": updated})


# ---------------------------------------------------------------------------
# Summary / stats endpoint
# ---------------------------------------------------------------------------
@api_view(["GET"])
def dashboard_stats(request):
    """Quick summary for the dashboard header cards."""
    tenant = request.query_params.get("tenant")
    qs = EmissionRecord.objects.all()
    if tenant:
        qs = qs.filter(tenant_id=tenant)

    total = qs.count()
    pending = qs.filter(status="PENDING").count()
    approved = qs.filter(status="APPROVED").count()
    rejected = qs.filter(status="REJECTED").count()
    flagged = qs.filter(status="FLAGGED").count()

    # Scope breakdown
    from django.db.models import Sum
    scope_totals = {}
    for scope_val in ["SCOPE_1", "SCOPE_2", "SCOPE_3"]:
        agg = qs.filter(scope=scope_val).aggregate(total_co2=Sum("emissions_kg_co2e"))
        scope_totals[scope_val] = float(agg["total_co2"] or 0)

    return Response({
        "total_records": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "flagged": flagged,
        "scope_emissions_kg": scope_totals,
    })


# ---------------------------------------------------------------------------
# File upload / ingestion endpoint
# ---------------------------------------------------------------------------
@api_view(["POST"])
def ingest_data(request):
    """
    Upload a file (SAP CSV, Utility CSV) or a JSON payload (Travel).

    Query params:
      - source_type: SAP | UTILITY | TRAVEL
      - tenant_id: integer
    """
    source_type = request.query_params.get("source_type", "").upper()
    tenant_id = request.query_params.get("tenant_id")

    if source_type not in ("SAP", "UTILITY", "TRAVEL"):
        return Response(
            {"error": "source_type must be SAP, UTILITY, or TRAVEL"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        tenant = Tenant.objects.get(pk=tenant_id)
    except (Tenant.DoesNotExist, ValueError, TypeError):
        return Response(
            {"error": f"Tenant {tenant_id} not found"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get file content
    file_obj = request.FILES.get("file")
    json_body = request.data.get("json_data")

    if file_obj:
        content = file_obj.read()
        file_name = file_obj.name
    elif json_body:
        content = json_body if isinstance(json_body, str) else str(json_body)
        file_name = "api_sync.json"
    else:
        return Response(
            {"error": "No file or json_data provided"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Create import record
    data_import = DataImport.objects.create(
        tenant=tenant,
        source_type=source_type,
        file_name=file_name,
        status="PROCESSING",
    )

    # Parse
    try:
        if source_type == "SAP":
            parsed_rows = parse_sap_csv(content)
        elif source_type == "UTILITY":
            parsed_rows = parse_utility_csv(content)
        elif source_type == "TRAVEL":
            parsed_rows = parse_travel_json(content)
        else:
            parsed_rows = []
    except Exception as e:
        data_import.status = "FAILED"
        data_import.error_summary = str(e)
        data_import.completed_at = timezone.now()
        data_import.save()
        return Response(
            {"error": f"Parsing failed: {e}", "import_id": data_import.pk},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Persist normalised records
    records = []
    failed = 0
    for row in parsed_rows:
        review_status = "FLAGGED" if row.get("flag_reason") else "PENDING"
        try:
            records.append(EmissionRecord(
                tenant=tenant,
                data_import=data_import,
                source_type=source_type,
                scope=row["scope"],
                activity_type=row["activity_type"],
                category=row.get("category", ""),
                quantity=row["quantity"],
                unit=row["unit"],
                emissions_kg_co2e=row.get("emissions_kg_co2e"),
                period_start=row.get("period_start"),
                period_end=row.get("period_end"),
                original_payload=row["original_payload"],
                status=review_status,
                flag_reason=row.get("flag_reason", ""),
            ))
        except Exception:
            failed += 1

    EmissionRecord.objects.bulk_create(records)

    data_import.total_rows = len(parsed_rows)
    data_import.failed_rows = failed
    data_import.status = "COMPLETED"
    data_import.completed_at = timezone.now()
    data_import.save()

    return Response({
        "import_id": data_import.pk,
        "total_rows": len(parsed_rows),
        "created": len(records),
        "failed": failed,
        "flagged": sum(1 for r in records if r.status == "FLAGGED"),
    }, status=status.HTTP_201_CREATED)
