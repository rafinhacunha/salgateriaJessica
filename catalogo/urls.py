from django.urls import path

from . import views

app_name = "catalogo"
urlpatterns = [
    path("", views.lista, name="lista"),
    path("novo/", views.criar, name="criar"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/situacao/", views.alternar_situacao, name="situacao"),
    path("<int:pk>/excluir/", views.excluir, name="excluir"),
]
