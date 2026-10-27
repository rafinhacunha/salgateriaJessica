from django.urls import path

from . import views

app_name = "estoque"
urlpatterns = [
    path("", views.consulta, name="consulta"),
    path("reposicao/", views.reposicao, name="reposicao"),
    path("ajuste/", views.ajuste, name="ajuste"),
    path("movimentos/", views.movimentos, name="movimentos"),
]
