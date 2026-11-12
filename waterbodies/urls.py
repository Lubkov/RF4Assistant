from django.urls import path

from . import views

app_name = "waterbodies"
urlpatterns = [path("<slug:slug>/", views.waterbody_detail, name="detail")]
