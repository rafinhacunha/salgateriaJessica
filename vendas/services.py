"""Regras de venda e pagamento centralizadas (RNF10)."""
import datetime

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from catalogo.models import Produto
from estoque import services as estoque
from nucleo.excecoes import RegraDeNegocio

from .models import ItemVenda, Pagamento, Venda


class ErroVenda(RegraDeNegocio):
    pass


def obter_venda_aberta(usuario):
    """RF05: cada atendente trabalha em uma venda aberta por vez."""
    venda = Venda.objects.filter(usuario=usuario, situacao=Venda.Situacao.ABERTA).order_by("-pk").first()
    return venda or Venda.objects.create(usuario=usuario)


def _exigir_aberta(venda):
    if venda.situacao != Venda.Situacao.ABERTA:
        raise ErroVenda("Esta venda já foi concluída e não pode ser alterada.")


def _validar_disponibilidade(produto, quantidade):
    """RF06 / RN07: produto ativo, com saldo, e quantidade dentro do saldo."""
    if not produto.ativo:
        raise ErroVenda(f"{produto.nome} está inativo e não pode ser vendido.")
    if produto.saldo == 0:
        raise ErroVenda(f"{produto.nome} está sem saldo.")
    if quantidade > produto.saldo:
        raise ErroVenda(f"Saldo insuficiente de {produto.nome}: restam {produto.saldo} {produto.unidade}(s).")


def _atualizar_total(venda):
    venda.total_centavos = venda.calcular_total()
    venda.save(update_fields=["total_centavos"])
    # Se os itens mudaram, o pagamento informado deixa de valer e deve ser refeito.
    Pagamento.objects.filter(venda=venda, confirmado=False).delete()


@transaction.atomic
def adicionar_item(venda, produto_id, quantidade):
    _exigir_aberta(venda)
    if quantidade < 1:
        raise ErroVenda("A quantidade deve ser um número inteiro positivo.")
    try:
        produto = Produto.objects.get(pk=produto_id)
    except Produto.DoesNotExist:
        raise ErroVenda("Produto não encontrado.")
    item = venda.itens.filter(produto=produto).first()
    nova_qtd = (item.quantidade if item else 0) + quantidade
    _validar_disponibilidade(produto, nova_qtd)
    if item:
        item.quantidade = nova_qtd
        item.save(update_fields=["quantidade"])
    else:
        item = ItemVenda.objects.create(
            venda=venda, produto=produto, quantidade=quantidade, preco_unitario_centavos=produto.preco_centavos
        )
    _atualizar_total(venda)
    return item


@transaction.atomic
def alterar_quantidade(item, quantidade):
    venda = item.venda
    _exigir_aberta(venda)
    if quantidade < 1:
        raise ErroVenda("A quantidade deve ser um número inteiro positivo. Use Remover para tirar o item.")
    _validar_disponibilidade(item.produto, quantidade)
    item.quantidade = quantidade
    item.save(update_fields=["quantidade"])
    _atualizar_total(venda)


@transaction.atomic
def remover_item(item):
    venda = item.venda
    _exigir_aberta(venda)
    item.delete()
    _atualizar_total(venda)


def calcular_troco(total_centavos, recebido_centavos):
    """RN03: dinheiro recebido >= total; troco = recebido - total."""
    if recebido_centavos is None:
        raise ErroVenda("Informe o valor recebido.")
    if recebido_centavos < total_centavos:
        raise ErroVenda("O valor recebido é menor que o total da venda.")
    return recebido_centavos - total_centavos


@transaction.atomic
def definir_pagamento(venda, meio, recebido_centavos=None):
    """RF08/RF09: um único meio por venda. Pix e cartão aguardam confirmação manual."""
    _exigir_aberta(venda)
    if not venda.itens.exists():
        raise ErroVenda("Inclua pelo menos um item para continuar.")
    if meio not in Pagamento.Meio.values:
        raise ErroVenda("Escolha a forma de pagamento.")
    if meio == Pagamento.Meio.DINHEIRO:
        troco = calcular_troco(venda.total_centavos, recebido_centavos)
    else:
        recebido_centavos, troco = None, 0  # troco só existe em dinheiro (E02)
    pagamento, _ = Pagamento.objects.update_or_create(
        venda=venda,
        defaults={"meio": meio, "valor_recebido_centavos": recebido_centavos, "troco_centavos": troco,
                  "confirmado": False, "confirmado_em": None},
    )
    return pagamento


@transaction.atomic
def concluir_venda(venda_id, usuario):
    """RF10/RF11: confirma o pagamento, congela a venda e baixa o estoque uma única vez.

    Tudo ocorre em uma transação: se qualquer etapa falhar, nada é gravado (RNF04).
    """
    venda = Venda.objects.select_for_update().get(pk=venda_id, usuario=usuario)
    if venda.situacao != Venda.Situacao.ABERTA:
        raise ErroVenda("Esta venda já foi concluída; o estoque não é baixado duas vezes.")
    itens = list(venda.itens.select_related("produto").order_by("produto_id"))
    if not itens:
        raise ErroVenda("A venda precisa de pelo menos um item.")
    pagamento = Pagamento.objects.filter(venda=venda).first()
    if pagamento is None:
        raise ErroVenda("Escolha a forma de pagamento antes de concluir.")

    total = sum(i.subtotal_centavos for i in itens)
    if pagamento.meio == Pagamento.Meio.DINHEIRO:
        pagamento.troco_centavos = calcular_troco(total, pagamento.valor_recebido_centavos)

    for item in itens:
        produto = Produto.objects.select_for_update().get(pk=item.produto_id)
        _validar_disponibilidade(produto, item.quantidade)
        estoque.baixar_por_venda(produto, item.quantidade, venda, usuario)

    agora = timezone.now()
    pagamento.confirmado, pagamento.confirmado_em = True, agora
    pagamento.save()
    venda.total_centavos, venda.data_hora, venda.situacao = total, agora, Venda.Situacao.CONCLUIDA
    venda.save()
    return venda


def relatorio(inicio, fim):
    """RF16: quantidade e total das vendas concluídas no período, por meio de pagamento."""
    vendas = Venda.objects.filter(
        situacao=Venda.Situacao.CONCLUIDA, data_hora__date__gte=inicio, data_hora__date__lte=fim
    )
    por_meio = {m: {"rotulo": r, "quantidade": 0, "total": 0} for m, r in Pagamento.Meio.choices}
    for linha in vendas.values("pagamento__meio").annotate(qtd=Count("id"), total=Sum("total_centavos")):
        por_meio[linha["pagamento__meio"]].update(quantidade=linha["qtd"], total=linha["total"])
    return {
        "vendas": vendas.select_related("usuario", "pagamento"),
        "por_meio": list(por_meio.values()),
        "quantidade": sum(m["quantidade"] for m in por_meio.values()),
        "total": sum(m["total"] for m in por_meio.values()),
    }


def periodo_padrao():
    hoje = timezone.localdate()
    return hoje, hoje
