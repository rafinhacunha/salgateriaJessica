from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("contas.urls")),
    path("catalogo/", include("catalogo.urls")),
    path("estoque/", include("estoque.urls")),
    path("", include("vendas.urls")),
]

handler403 = "nucleo.views.acesso_negado"
