from django.urls import path

from . import views

app_name = "presences"

urlpatterns = [
    path("", views.presence_index, name="index"),
    path("seances/<int:seance_id>/", views.presence_sheet, name="sheet"),
]
