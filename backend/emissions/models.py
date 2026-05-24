"""
Emissions data models.

Designed for:
- Multi-tenancy (each client is a Tenant)
- Source-of-truth tracking (DataImport links every row to its origin file/API call)
- Scope 1/2/3 categorisation
- Audit trail (status workflow + timestamps + original_payload)
- Unit normalisation (stored in a canonical unit per activity type)
"""

from django.db import models


class Tenant(models.Model):
    """
    Represents a client company.  Every piece of data belongs to exactly one tenant,
    so analysts from different organisations never see each other's records.
    """
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DataImport(models.Model):
    """
    One row per ingestion event — a file upload or an API sync.
    Captures *what* was ingested, *when*, and *how many* rows came out of it.
    """

    class SourceType(models.TextChoices):
        SAP = "SAP", "SAP (Fuel & Procurement)"
        UTILITY = "UTILITY", "Utility (Electricity)"
        TRAVEL = "TRAVEL", "Corporate Travel"

    class Status(models.TextChoices):
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="imports")
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    file_name = models.CharField(max_length=512, blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PROCESSING)
    total_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.source_type} import #{self.pk} ({self.status})"


class EmissionRecord(models.Model):
    """
    The normalised, canonical record.

    Every row ingested from any source is mapped into this schema so that
    the analyst dashboard can present a single, consistent view.
    """

    class Scope(models.TextChoices):
        SCOPE_1 = "SCOPE_1", "Scope 1 — Direct"
        SCOPE_2 = "SCOPE_2", "Scope 2 — Indirect (Energy)"
        SCOPE_3 = "SCOPE_3", "Scope 3 — Value Chain"

    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        FLAGGED = "FLAGGED", "Flagged for Review"

    # Ownership
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="records")
    data_import = models.ForeignKey(DataImport, on_delete=models.CASCADE, related_name="records")

    # Classification
    source_type = models.CharField(max_length=16, choices=DataImport.SourceType.choices)
    scope = models.CharField(max_length=16, choices=Scope.choices)
    activity_type = models.CharField(max_length=128, help_text="e.g. Electricity, Flight, Diesel, Hotel")
    category = models.CharField(max_length=128, blank=True, default="", help_text="Sub-category for grouping")

    # Normalised quantities
    quantity = models.DecimalField(max_digits=16, decimal_places=4)
    unit = models.CharField(max_length=32, help_text="Canonical unit: kWh, liters, km, kg, etc.")
    emissions_kg_co2e = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True,
        help_text="Computed or source-provided CO₂-equivalent in kg"
    )

    # Temporal
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    # Provenance — the raw data exactly as received
    original_payload = models.JSONField(
        help_text="Verbatim row from the source file/API before normalisation"
    )

    # Review workflow
    status = models.CharField(max_length=16, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    reviewer_notes = models.TextField(blank=True, default="")
    flag_reason = models.CharField(max_length=256, blank=True, default="")

    # Audit timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["source_type"]),
            models.Index(fields=["scope"]),
        ]

    def __str__(self):
        return f"{self.activity_type} | {self.quantity} {self.unit} | {self.status}"
