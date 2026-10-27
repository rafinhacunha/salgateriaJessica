from django.db import models
from django.utils import timezone


class MovimentoEstoque(models.Model):
    """Histórico de movimentos: entrada, saída (venda) e ajuste (RF13-RF15).

    `quantidade` é a variação do saldo: positiva (entrada), negativa (saída) ou
    com sinal conforme a contagem (ajuste).
    """

    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SAIDA = "SAIDA", "Saída (venda)"
        AJUSTE = "AJUSTE", "Ajuste"

    produto = models.ForeignKey("catalogo.Produto", on_delete=models.PROTECT, related_name="movimentos")
    tipo = models.CharField(max_length=7, choices=Tipo.choices)
    quantidade = models.IntegerField()
    saldo_anterior = models.PositiveIntegerField()
    saldo_posterior = models.PositiveIntegerField()
    data_hora = models.DateTimeField(default=timezone.now)
    motivo = models.CharField(max_length=200)
    usuario = models.ForeignKey("contas.Usuario", on_delete=models.PROTECT, related_name="movimentos")
    venda = models.ForeignKey("vendas.Venda", null=True, blank=True, on_delete=models.PROTECT, related_name="movimentos")

    class Meta:
        ordering = ["-data_hora", "-pk"]
        constraints = [
            # RNF09: baixa duplicada do mesmo evento é impossível no banco
            models.UniqueConstraint(
                fields=["venda", "produto"], condition=models.Q(tipo="SAIDA"), name="uma_baixa_por_item_de_venda"
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.quantidade:+d} de {self.produto}"
