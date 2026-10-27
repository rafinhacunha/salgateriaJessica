"""Regras de estoque centralizadas (RNF10). Todo saldo muda por aqui, com histórico."""
from django.db import transaction

from catalogo.models import Produto
from nucleo.excecoes import RegraDeNegocio

from .models import MovimentoEstoque


class ErroEstoque(RegraDeNegocio):
    pass


def _registrar(produto, tipo, variacao, motivo, usuario, venda=None):
    """Aplica a variação ao saldo do produto (já bloqueado) e grava o movimento."""
    anterior = produto.saldo
    posterior = anterior + variacao
    if posterior < 0:
        raise ErroEstoque(f"Saldo insuficiente de {produto.nome}: restam {anterior}.")
    produto.saldo = posterior
    produto.save(update_fields=["saldo"])
    return MovimentoEstoque.objects.create(
        produto=produto, tipo=tipo, quantidade=variacao, saldo_anterior=anterior,
        saldo_posterior=posterior, motivo=motivo, usuario=usuario, venda=venda,
    )


@transaction.atomic
def registrar_entrada(produto_id, quantidade, motivo, usuario):
    if quantidade <= 0:
        raise ErroEstoque("A quantidade de entrada deve ser maior que zero.")
    produto = Produto.objects.select_for_update().get(pk=produto_id)
    return _registrar(produto, MovimentoEstoque.Tipo.ENTRADA, quantidade, motivo, usuario)


@transaction.atomic
def registrar_ajuste(produto_id, saldo_contado, motivo, usuario):
    if saldo_contado < 0:
        raise ErroEstoque("O saldo contado não pode ser negativo.")
    if not motivo.strip():
        raise ErroEstoque("Informe o motivo do ajuste.")
    produto = Produto.objects.select_for_update().get(pk=produto_id)
    diferenca = saldo_contado - produto.saldo
    if diferenca == 0:
        raise ErroEstoque("O saldo contado é igual ao saldo atual; não há o que ajustar.")
    return _registrar(produto, MovimentoEstoque.Tipo.AJUSTE, diferenca, motivo, usuario)


def baixar_por_venda(produto, quantidade, venda, usuario):
    """Chamada dentro da transação de conclusão da venda (RF11)."""
    return _registrar(produto, MovimentoEstoque.Tipo.SAIDA, -quantidade, f"Venda {venda.identificador}", usuario, venda)
