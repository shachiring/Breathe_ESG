"""
Management command to seed the database with a demo tenant and sample data.
Usage:  python manage.py seed_demo
"""

# import os
from pathlib import Path
from django.core.management.base import BaseCommand
from emissions.models import Tenant


class Command(BaseCommand):
    help = "Create a demo tenant and ingest sample data files."

    def handle(self, *args, **options):
        # 1. Create or get demo tenant
        tenant, created = Tenant.objects.get_or_create(
            name="Acme Corp",
            defaults={"industry": "Manufacturing"},
        )
        status_msg = "Created" if created else "Already exists"
        self.stdout.write(f"  Tenant: {tenant.name} ({status_msg})")

        sample_dir = Path(__file__).resolve().parent.parent.parent.parent / "sample_data"

        # 2. Ingest each sample file via the parser pipeline
        from emissions.ingestion.sap import parse_sap_csv
        from emissions.ingestion.utility import parse_utility_csv
        from emissions.ingestion.travel import parse_travel_json
        from emissions.models import DataImport, EmissionRecord
        from django.utils import timezone

        files = [
            ("SAP", "sap_export.csv", parse_sap_csv),
            ("UTILITY", "utility_export.csv", parse_utility_csv),
            ("TRAVEL", "travel_bookings.json", parse_travel_json),
        ]

        for source_type, filename, parser in files:
            filepath = sample_dir / filename
            if not filepath.exists():
                self.stdout.write(self.style.WARNING(f"  Skipped {filename} — not found"))
                continue

            content = filepath.read_bytes()
            data_import = DataImport.objects.create(
                tenant=tenant,
                source_type=source_type,
                file_name=filename,
                status="PROCESSING",
            )

            parsed = parser(content)
            records = []
            for row in parsed:
                review_status = "FLAGGED" if row.get("flag_reason") else "PENDING"
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

            EmissionRecord.objects.bulk_create(records)
            data_import.total_rows = len(parsed)
            data_import.failed_rows = 0
            data_import.status = "COMPLETED"
            data_import.completed_at = timezone.now()
            data_import.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"  {source_type}: {len(records)} records ingested "
                    f"({sum(1 for r in records if r.status == 'FLAGGED')} flagged)"
                )
            )

        self.stdout.write(self.style.SUCCESS("\nDemo seed complete!"))
