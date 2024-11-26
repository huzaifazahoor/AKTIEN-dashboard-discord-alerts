# views.py
from django.db.models import Count
from django.views.generic import DetailView, ListView

from stocks.models import Stock

from .models import Alert


class AlertListView(ListView):
    model = Alert
    template_name = "alerts/alert_list.html"
    context_object_name = "alerts"

    def get_queryset(self):
        # Group alerts by name and count stocks
        return (
            Alert.objects.values("alert_name")
            .annotate(stock_count=Count("stock", distinct=True))
            .order_by("alert_name")
        )


class AlertDetailView(DetailView):
    template_name = "alerts/alert_detail.html"
    context_object_name = "alert_data"

    def get_object(self):
        alert_name = self.kwargs.get("alert_name")
        # Get all stocks for this alert name
        return {
            "alert_name": alert_name,
            "stocks": Stock.objects.filter(alerts__alert_name=alert_name)
            .select_related("info")
            .prefetch_related("alerts")
            .distinct(),
        }
