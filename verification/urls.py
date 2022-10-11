from django.urls import path
from . import views


app_name = "verification"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("verify/", views.verify, name="verify"),
]
