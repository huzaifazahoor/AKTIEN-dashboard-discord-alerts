from django.db import models


class Alert(models.Model):
    stock = models.ForeignKey(
        "stocks.Stock", related_name="alerts", on_delete=models.CASCADE
    )
    alert_name = models.CharField(max_length=50)
    alert_datetime = models.DateTimeField()
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["stock", "alert_name", "alert_datetime"]

    def __str__(self):
        return f"{self.alert_name} {self.stock.ticker}"
