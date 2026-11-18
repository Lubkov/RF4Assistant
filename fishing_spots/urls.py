from django.urls import path
from . import views

app_name = 'fishing_spots'
urlpatterns = [path('', views.list_spots, name='list'), path('options/', views.options, name='options'), path('create/', views.create, name='create')]
