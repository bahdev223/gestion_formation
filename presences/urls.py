from django.urls import path

from .views import PresenceIndexView

app_name = "presences"

urlpatterns = [
    path("", PresenceIndexView.as_view(), name="index"),
]
