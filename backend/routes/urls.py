from django.urls import path

from . import views

urlpatterns = [
    path("", views.health, name="health"),
    path("health/", views.health, name="health-alt"),
    path("stations/", views.stations_summary, name="stations-summary"),
    path("route/", views.plan_route, name="plan-route"),
]
