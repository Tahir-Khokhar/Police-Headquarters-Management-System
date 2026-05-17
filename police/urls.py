from django.urls import path

from . import views

urlpatterns = [
    path('', views.personnel_dashboard, name='personnel_dashboard'),
    path('application/', views.application_list, name='application_list'),
]


