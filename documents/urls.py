from django.urls import path

from .views import DocumentIndexView

app_name = "documents"

urlpatterns = [
    path("", DocumentIndexView.as_view(), name="index"),
]
