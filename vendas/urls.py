from django.urls import path

from . import views

app_name = "vendas"
urlpatterns = [
    path("", views.nova_venda, name="nova"),
    path("venda/item/adicionar/", views.adicionar_item, name="adicionar"),
    path("venda/item/<int:pk>/alterar/", views.alterar_item, name="alterar"),
    path("venda/item/<int:pk>/remover/", views.remover_item, name="remover"),
    path("venda/pagamento/", views.pagamento, name="pagamento"),
    path("venda/registro/", views.registro, name="registro"),
    path("venda/<int:pk>/comprovante/", views.comprovante, name="comprovante"),
    path("vendas/", views.lista, name="lista"),
    path("relatorio/", views.relatorio, name="relatorio"),
]
