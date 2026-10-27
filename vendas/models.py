from django.db import models
from django.db.models import F, Sum
from django.utils import timezone


class Venda(models.Model):
    class Situacao(models.TextChoices):
        ABERTA = "ABERTA", "Aberta"
        CONCLUIDA = "CONCLUIDA", "Concluída"

    usuario = models.ForeignKey("contas.Usuario", on_delete=models.PROTECT, related_name="vendas")
    data_hora = models.DateTimeField(default=timezone.now)
    total_centavos = models.PositiveIntegerField(default=0)
    situacao = models.CharField(max_length=10, choices=Situacao.choices, default=Situacao.ABERTA)

    class Meta:
        ordering = ["-data_hora", "-pk"]

    def __str__(self):
        return self.identificador

    @property
    def identificador(self):
        return f"V-{self.pk:06d}"

    @property
    def concluida(self):
        return self.situacao == self.Situacao.CONCLUIDA

    def calcular_total(self):
        """total = soma dos subtotais (RF07), em centavos."""
        total = self.itens.aggregate(t=Sum(F("quantidade") * F("preco_unitario_centavos")))["t"] or 0
        return int(total)


class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey("catalogo.Produto", on_delete=models.PROTECT, related_name="itens_venda")
    quantidade = models.PositiveIntegerField()
    # Preço no momento da venda: mudanças futuras no catálogo não o alteram (RN05)
    preco_unitario_centavos = models.PositiveIntegerField()

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(fields=["venda", "produto"], name="produto_unico_por_venda"),
            models.CheckConstraint(condition=models.Q(quantidade__gt=0), name="item_quantidade_positiva"),
        ]

    def __str__(self):
        return f"{self.quantidade} x {self.produto}"

    @property
    def subtotal_centavos(self):
        return self.quantidade * self.preco_unitario_centavos


class Pagamento(models.Model):
    class Meio(models.TextChoices):
        DINHEIRO = "DINHEIRO", "Dinheiro"
        PIX = "PIX", "Pix"
        CARTAO = "CARTAO", "Cartão"

    venda = models.OneToOneField(Venda, on_delete=models.CASCADE, related_name="pagamento")
    meio = models.CharField(max_length=8, choices=Meio.choices)
    # Só valores e a confirmação: nunca PAN, CVV ou segredo Pix (RNF07)
    valor_recebido_centavos = models.PositiveIntegerField(null=True, blank=True)
    troco_centavos = models.PositiveIntegerField(default=0)
    confirmado = models.BooleanField(default=False)
    confirmado_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_meio_display()} - {self.venda}"
