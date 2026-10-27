from django.db import models


class Produto(models.Model):
    """Produto vendável (RF03). Estoque por unidade vendável (RN01)."""

    class Unidade(models.TextChoices):
        UNIDADE = "unidade", "unidade"
        PACOTE = "pacote", "pacote"
        PORCAO = "porção", "porção"
        COPO = "copo", "copo"

    nome = models.CharField(max_length=100)
    categoria = models.CharField(max_length=40)
    unidade = models.CharField("unidade vendável", max_length=10, choices=Unidade.choices, default=Unidade.UNIDADE)
    preco_centavos = models.PositiveIntegerField("preço (centavos)")
    saldo = models.PositiveIntegerField(default=0)  # nunca negativo (RNF09)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        constraints = [
            models.CheckConstraint(condition=models.Q(preco_centavos__gt=0), name="produto_preco_maior_que_zero"),
        ]

    def __str__(self):
        return self.nome

    def esta_disponivel(self, qtd=1):
        return self.ativo and 0 < qtd <= self.saldo

    @property
    def pode_excluir(self):
        """Só é possível excluir produto sem histórico; senão, inativar (RN07)."""
        return not self.movimentos.exists() and not self.itens_venda.exists()
