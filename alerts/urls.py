from django.urls import path

from .views import AlertDetailView, AlertListView

urlpatterns = [
    path("", AlertListView.as_view(), name="alert_list"),
    path("<str:alert_name>/", AlertDetailView.as_view(), name="alert_detail"),
]
