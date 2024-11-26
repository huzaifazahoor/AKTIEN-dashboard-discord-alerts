from django.db import models


class Stock(models.Model):
    ticker = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=200)
    exchange = models.CharField(max_length=20)
    sector = models.CharField(max_length=100)
    industry = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.ticker


class StockInfo(models.Model):
    stock = models.OneToOneField(Stock, related_name="info", on_delete=models.CASCADE)
    market_cap = models.DecimalField(max_digits=15, decimal_places=2)
    avg_volume = models.BigIntegerField()
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_volume = models.BigIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.stock.ticker
