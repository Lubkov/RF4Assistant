from django.urls import path
from . import views

app_name = "records"
urlpatterns = [
    path("", views.weekly_report, name="weekly"),
    path("fish-details/", views.weekly_report, {"fish_details": True}, name="fish_details"),
    path("bait-details/", views.weekly_report, {"bait_details": True}, name="bait_details"),
]
