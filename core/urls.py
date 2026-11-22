from django.urls import path
from . import views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("shop-prices/", views.shop_prices, name="shop_prices"),
]
