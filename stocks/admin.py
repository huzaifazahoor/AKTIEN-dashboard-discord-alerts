from django.contrib import admin

from .models import Stock, StockInfo

admin.site.register(Stock)
admin.site.register(StockInfo)
