from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.views.generic import ListView

from stocks.models import Stock

from .models import Alert


class AlertListView(LoginRequiredMixin, ListView):
    model = Alert
    template_name = "alerts/alert_list.html"
    context_object_name = "alerts"
    paginate_by = 10

    def get_queryset(self):
        return (
            Alert.objects.values("alert_name")
            .annotate(stock_count=Count("stock", distinct=True))
            .order_by("alert_name")
        )


class AlertDetailView(LoginRequiredMixin, ListView):
    template_name = "alerts/alert_detail.html"
    context_object_name = "stocks"
    paginate_by = 10

    def get_queryset(self):
        alert_name = self.kwargs.get("alert_name")
        return (
            Stock.objects.filter(alerts__alert_name=alert_name)
            .select_related("info")
            .prefetch_related("alerts")
            .distinct()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["alert_data"] = {
            "alert_name": self.kwargs.get("alert_name"),
            "stocks": context["stocks"],
            "total_stocks": self.get_queryset().count(),
        }
        return context
