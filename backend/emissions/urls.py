"""URL routing for the emissions app."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"tenants", views.TenantViewSet)
router.register(r"imports", views.DataImportViewSet, basename="dataimport")
router.register(r"records", views.EmissionRecordViewSet, basename="emissionrecord")

urlpatterns = [
    path("", include(router.urls)),
    path("ingest/", views.ingest_data, name="ingest-data"),
    path("stats/", views.dashboard_stats, name="dashboard-stats"),
]
