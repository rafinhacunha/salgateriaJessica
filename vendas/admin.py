from django.contrib import admin

from .models import ItemVenda, Pagamento, Venda


class ItemInline(admin.TabularInline):
    model = ItemVenda
    extra = 0
    can_delete = False
    readonly_fields = ("produto", "quantidade", "preco_unitario_centavos")


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ("identificador", "data_hora", "usuario", "total_centavos", "situacao")
    list_filter = ("situacao",)
    inlines = [ItemInline]
