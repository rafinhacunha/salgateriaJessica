from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from catalogo.models import Produto
from contas.decorators import proprietaria_required
from nucleo.excecoes import RegraDeNegocio
from nucleo.utils import normalizar

from . import services
from .forms import PagamentoForm, PeriodoForm
from .models import ItemVenda, Pagamento, Venda


def _contexto_pedido(venda):
    itens = list(venda.itens.select_related("produto"))
    return {
        "venda": venda, "itens": itens, "total": venda.total_centavos,
        "qtd_itens": len(itens), "qtd_unidades": sum(i.quantidade for i in itens),
    }


@login_required
def nova_venda(request):
    """Passo 1: buscar produtos e montar o pedido (HU03, HU04)."""
    venda = services.obter_venda_aberta(request.user)
    q = request.GET.get("q", "").strip()
    categoria = request.GET.get("categoria", "").strip()
    buscou = "q" in request.GET or "categoria" in request.GET

    ativos = Produto.objects.filter(ativo=True)
    resultados = None
    if buscou:
        resultados = [
            p for p in ativos.order_by("nome")
            if (not q or normalizar(q) in normalizar(p.nome)) and (not categoria or p.categoria == categoria)
        ]
    contexto = _contexto_pedido(venda)
    contexto.update({
        "q": q, "categoria": categoria, "buscou": buscou, "resultados": resultados,
        "categorias": ativos.order_by("categoria").values_list("categoria", flat=True).distinct(),
        "no_pedido": {i.produto_id: i.quantidade for i in contexto["itens"]},
    })
    return render(request, "vendas/nova_venda.html", contexto)


def _voltar_busca(request):
    params = {k: request.POST.get(k, "") for k in ("q", "categoria") if k in request.POST}
    return reverse("vendas:nova") + ("?" + urlencode(params) if params else "")


@login_required
@require_POST
def adicionar_item(request):
    venda = services.obter_venda_aberta(request.user)
    try:
        produto_id, qtd = int(request.POST["produto"]), int(request.POST.get("quantidade", 1))
    except (KeyError, ValueError):
        messages.error(request, "Informe uma quantidade inteira positiva.")
        return redirect(_voltar_busca(request))
    try:
        item = services.adicionar_item(venda, produto_id, qtd)
    except RegraDeNegocio as erro:
        messages.error(request, str(erro))
    else:
        messages.success(request, f"{qtd} × {item.produto.nome} adicionado(s) ao pedido.")
    return redirect(_voltar_busca(request))


def _item_do_usuario(request, pk):
    return get_object_or_404(
        ItemVenda.objects.select_related("produto", "venda"),
        pk=pk, venda__usuario=request.user, venda__situacao=Venda.Situacao.ABERTA,
    )


@login_required
@require_POST
def alterar_item(request, pk):
    item = _item_do_usuario(request, pk)
    nova = item.quantidade + (1 if request.POST.get("acao") == "mais" else -1)
    try:
        services.alterar_quantidade(item, nova)
    except RegraDeNegocio as erro:
        messages.error(request, str(erro))
    return redirect(_voltar_busca(request))


@login_required
@require_POST
def remover_item(request, pk):
    item = _item_do_usuario(request, pk)
    services.remover_item(item)
    messages.success(request, f"{item.produto.nome} removido do pedido.")
    return redirect(_voltar_busca(request))


@login_required
def pagamento(request):
    """Passo 2: forma de pagamento e valor recebido (HU06)."""
    venda = services.obter_venda_aberta(request.user)
    if not venda.itens.exists():
        messages.error(request, "Inclua pelo menos um item para continuar.")
        return redirect("vendas:nova")
    atual = Pagamento.objects.filter(venda=venda).first()
    inicial = {"meio": atual.meio if atual else Pagamento.Meio.DINHEIRO}
    if atual and atual.valor_recebido_centavos:
        from nucleo.utils import centavos_para_campo
        inicial["valor_recebido"] = centavos_para_campo(atual.valor_recebido_centavos)

    form = PagamentoForm(request.POST or None, initial=inicial, total_centavos=venda.total_centavos)
    if request.method == "POST" and form.is_valid():
        try:
            services.definir_pagamento(venda, form.cleaned_data["meio"], form.cleaned_data["valor_recebido"])
        except RegraDeNegocio as erro:
            form.add_error(None, str(erro))
        else:
            return redirect("vendas:registro")

    total = venda.total_centavos
    sugestoes = sorted({total, *(-(-total // base) * base for base in (1000, 2000, 5000, 10000))})[:4]
    meio_atual = form["meio"].value() or Pagamento.Meio.DINHEIRO
    contexto = _contexto_pedido(venda)
    contexto.update({
        "form": form, "meio_atual": meio_atual, "sugestoes": sugestoes,
        "meios": [
            ("DINHEIRO", "Dinheiro", "Informe o valor recebido e veja o troco."),
            ("PIX", "Pix", "Confirme o recebimento manualmente."),
            ("CARTAO", "Cartão", "Confirme o recebimento na maquininha."),
        ],
    })
    return render(request, "vendas/pagamento.html", contexto)


@login_required
def registro(request):
    """Passo 3: conferir e concluir a venda (HU06, HU07, HU08)."""
    venda = services.obter_venda_aberta(request.user)
    pag = Pagamento.objects.filter(venda=venda).first()
    if not venda.itens.exists():
        return redirect("vendas:nova")
    if pag is None:
        messages.error(request, "Escolha a forma de pagamento.")
        return redirect("vendas:pagamento")

    if request.method == "POST":
        if pag.meio != Pagamento.Meio.DINHEIRO and not request.POST.get("confirmo"):
            messages.error(request, "Marque que o recebimento foi verificado antes de registrar a venda.")
        else:
            try:
                concluida = services.concluir_venda(venda.pk, request.user)
            except RegraDeNegocio as erro:
                messages.error(request, str(erro))
                return redirect("vendas:nova")
            return redirect("vendas:comprovante", pk=concluida.pk)

    contexto = _contexto_pedido(venda)
    contexto["pagamento"] = pag
    return render(request, "vendas/registro.html", contexto)


@login_required
def comprovante(request, pk):
    """Passo 4: comprovante (HU08, RF12)."""
    venda = get_object_or_404(
        Venda.objects.select_related("usuario", "pagamento"), pk=pk, situacao=Venda.Situacao.CONCLUIDA
    )
    if venda.usuario_id != request.user.pk and not request.user.eh_proprietaria:
        raise PermissionDenied
    return render(request, "vendas/comprovante.html", {"venda": venda, "itens": venda.itens.select_related("produto")})


@login_required
def lista(request):
    vendas = Venda.objects.filter(situacao=Venda.Situacao.CONCLUIDA).select_related("usuario", "pagamento")
    if not request.user.eh_proprietaria:
        vendas = vendas.filter(usuario=request.user)
    pagina = Paginator(vendas, 20).get_page(request.GET.get("pagina"))
    return render(request, "vendas/lista.html", {"pagina": pagina})


@proprietaria_required
def relatorio(request):
    inicio, fim = services.periodo_padrao()
    form = PeriodoForm(request.GET or {"inicio": inicio, "fim": fim})
    if form.is_valid():
        inicio, fim = form.cleaned_data["inicio"], form.cleaned_data["fim"]
    dados = services.relatorio(inicio, fim) if form.is_valid() else None
    return render(request, "vendas/relatorio.html", {"form": form, "dados": dados, "inicio": inicio, "fim": fim})
