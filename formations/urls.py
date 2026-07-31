from django.urls import path

from .views import (
    CategorieCreateView,
    CategorieListView,
    FormationCreateView,
    FormationDeleteView,
    FormationUpdateView,
    FormationIndexView,
    SeanceCreateView,
    SeanceListView,
    SessionCreateView,
    SessionDetailView,
    SessionListView,
)

app_name = "formations"

urlpatterns = [
    path("", FormationIndexView.as_view(), name="index"),
    path("create/", FormationCreateView.as_view(), name="create"),
    path("<int:pk>/modifier/", FormationUpdateView.as_view(), name="update"),
    path("<int:pk>/supprimer/", FormationDeleteView.as_view(), name="delete"),
    path("categories/", CategorieListView.as_view(), name="categorie-list"),
    path(
        "categories/create/",
        CategorieCreateView.as_view(),
        name="categorie-create",
    ),
    path("sessions/", SessionListView.as_view(), name="session-list"),
    path("sessions/create/", SessionCreateView.as_view(), name="session-create"),
    path("sessions/<int:pk>/", SessionDetailView.as_view(), name="session-detail"),
    path("seances/", SeanceListView.as_view(), name="seance-list"),
    path("seances/create/", SeanceCreateView.as_view(), name="seance-create"),
]
