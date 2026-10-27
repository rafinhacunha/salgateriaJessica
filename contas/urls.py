from django.urls import path

from . import views

app_name = "contas"
urlpatterns = [
    path("entrar/", views.EntrarView.as_view(), name="login"),
    path("sair/", views.SairView.as_view(), name="sair"),
]
