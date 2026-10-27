from django.contrib import admin

from .models import Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "preco_centavos", "saldo", "ativo")
    list_filter = ("categoria", "ativo")
    search_fields = ("nome",)
    readonly_fields = ("saldo",)  # saldo só muda por reposição, ajuste ou venda
