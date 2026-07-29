from django.urls import path

from .views import ParticipantCreateView, ParticipantIndexView

app_name = "participants"

urlpatterns = [
    path("", ParticipantIndexView.as_view(), name="index"),
    path("create/", ParticipantCreateView.as_view(), name="create"),
]
