from django.urls import path

from .views import (
    InscriptionCreateView,
    InscriptionIndexView,
    NouvelApprenantInscriptionView,
)

app_name = "inscriptions"

urlpatterns = [
    path("", InscriptionIndexView.as_view(), name="index"),
    path("create/", InscriptionCreateView.as_view(), name="create"),
    path(
        "create-apprenant/",
        NouvelApprenantInscriptionView.as_view(),
        name="create-learner",
    ),
]
