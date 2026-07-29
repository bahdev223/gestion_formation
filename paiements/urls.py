from django.urls import path

from .views import PaiementCreateView, PaiementDetailView, PaiementIndexView

app_name = "paiements"

urlpatterns = [
    path("", PaiementIndexView.as_view(), name="index"),
    path("create/", PaiementCreateView.as_view(), name="create"),
    path("<int:pk>/", PaiementDetailView.as_view(), name="detail"),
]
