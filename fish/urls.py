from django.urls import path

from . import views

app_name = "fish"
urlpatterns = [path("", views.fish_list, name="list")]
