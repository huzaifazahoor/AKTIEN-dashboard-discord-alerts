from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from .models import Stock


class StockListView(LoginRequiredMixin, ListView):
    model = Stock
    template_name = "stocks/stock_list.html"
    context_object_name = "stocks"
    paginate_by = 10

    def get_queryset(self):
        return Stock.objects.select_related("info").order_by("ticker")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add alert counts for each stock
        for stock in context["stocks"]:
            stock.alert_count = stock.alerts.count()
        return context
