from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from catalogo.models import Produto
from contas.decorators import proprietaria_required
from nucleo.excecoes import RegraDeNegocio
from nucleo.utils import normalizar

from . import services
from .forms import AjusteForm, EntradaForm
from .models import MovimentoEstoque
from django.contrib.auth.decorators import login_required


@login_required
def consulta(request):
    """Consulta de estoque, aberta a todos os perfis."""
    q = request.GET.get("q", "").strip()
    produtos = Produto.objects.order_by("-ativo", "categoria", "nome")
    if q:
        produtos = [p for p in produtos if normalizar(q) in normalizar(p.nome + " " + p.categoria)]
    return render(request, "estoque/consulta.html", {"produtos": produtos, "q": q})


def _processar(request, form_class, acao, titulo, texto_botao, sucesso):
    inicial = {"produto": request.GET.get("produto")} if request.method == "GET" else None
    form = form_class(request.POST or None, initial=inicial)
    if form.is_valid():
        dados = form.cleaned_data
        try:
            mov = acao(dados["produto"].pk, dados.get("quantidade", dados.get("saldo_contado")), dados["motivo"], request.user)
        except RegraDeNegocio as erro:
            form.add_error(None, str(erro))
        else:
            messages.success(request, sucesso(mov))
            return redirect("estoque:consulta")
    return render(request, "estoque/movimento_form.html", {"form": form, "titulo": titulo, "botao": texto_botao})


@proprietaria_required
def reposicao(request):
    return _processar(
        request, EntradaForm, services.registrar_entrada, "Registrar reposição", "Registrar entrada",
        lambda m: f"Entrada de {m.quantidade} un. em {m.produto.nome}. Saldo: {m.saldo_posterior}.",
    )


@proprietaria_required
def ajuste(request):
    return _processar(
        request, AjusteForm, services.registrar_ajuste, "Ajustar inventário", "Registrar ajuste",
        lambda m: f"Saldo de {m.produto.nome} ajustado de {m.saldo_anterior} para {m.saldo_posterior}.",
    )


@proprietaria_required
def movimentos(request):
    qs = MovimentoEstoque.objects.select_related("produto", "usuario")
    produto_id = request.GET.get("produto", "")
    tipo = request.GET.get("tipo", "")
    if produto_id.isdigit():
        qs = qs.filter(produto_id=produto_id)
    if tipo in MovimentoEstoque.Tipo.values:
        qs = qs.filter(tipo=tipo)
    pagina = Paginator(qs, 25).get_page(request.GET.get("pagina"))
    return render(request, "estoque/movimentos.html", {
        "pagina": pagina, "produtos": Produto.objects.order_by("nome"), "tipos": MovimentoEstoque.Tipo.choices,
        "produto_id": produto_id, "tipo": tipo,
    })
