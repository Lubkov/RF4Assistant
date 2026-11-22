from django.shortcuts import render

from waterbodies.models import Waterbody


# Column order matches the headings in core/shop_prices.html.
SHOP_PRICES = (
    ("оз. Комариное", (100, 100, 100, 100, 90)),
    ("оз. Лосиное", (100, 100, 100, 100, 90)),
    ("р. Вьюнок", (100, 100, 85, 100, 90)),
    ("оз. Старый Острог", (110, 105, 90, 100, 80)),
    ("р. Белая", (110, 110, 100, 100, 100)),
    ("оз. Куори", (110, 115, 135, 150, 130)),
    ("оз. Медвежье", (115, None, None, None, 130)),
    ("р. Волхов", (115, 100, 100, 100, 100)),
    ("р. Северский Донец", (116, 100, 100, 100, 100)),
    ("р. Сура", (117, 100, 110, 100, 100)),
    ("Ладожское оз.", (120, 110, 125, 110, 125)),
    ("оз. Янтарное", (120, 103, 110, 105, 120)),
    ("Ладожский архипелаг", (120, 113, 137, None, 150)),
    ("оз. Медное", (120, 104, None, None, None)),
    ("р. Ахтуба", (120, 100, 100, 100, 130)),
    ("р. Нижняя Тунгуска", (120, 100, 110, 100, 130)),
    ("р. Яма", (120, 100, 100, 100, 130)),
    ("Норвежское море", (120, 100, 150, 116, 200)),
)


def home(request):
    waterbodies = Waterbody.objects.filter(is_active=True).order_by("sort_order", "name", "id")
    return render(request, "core/home.html", {"waterbodies": waterbodies})


def shop_prices(request):
    return render(request, "core/shop_prices.html", {"shop_prices": SHOP_PRICES})
