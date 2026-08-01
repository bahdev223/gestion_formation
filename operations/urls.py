from django.urls import path

from . import views

app_name = "operations"

urlpatterns = [
    path("", views.OperationIndexView.as_view(), name="index"),
    path("nouvelle/", views.OperationCreateView.as_view(), name="create"),
    path("<int:pk>/", views.OperationDetailView.as_view(), name="detail"),
    path("<int:pk>/modifier/", views.OperationUpdateView.as_view(), name="update"),
    path("<int:pk>/valider/", views.valider_operation, name="valider"),
    path("<int:pk>/annuler/", views.annuler_operation, name="annuler"),
]
