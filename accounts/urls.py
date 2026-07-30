from django.urls import path

from .views import MandatoryPasswordChangeView, UserLoginView, UserLogoutView

app_name = "accounts"

urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path(
        "change-password/",
        MandatoryPasswordChangeView.as_view(),
        name="change-password",
    ),
    path("logout/", UserLogoutView.as_view(), name="logout"),
]
