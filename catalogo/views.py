from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from contas.decorators import proprietaria_required
from nucleo.utils import normalizar

from .forms import ProdutoForm
from .models import Produto


@proprietaria_required
def lista(request):
    q = request.GET.get("q", "").strip()
    produtos = Produto.objects.order_by("-ativo", "nome")
    if q:
        produtos = [p for p in produtos if normalizar(q) in normalizar(p.nome + " " + p.categoria)]
    return render(request, "catalogo/lista.html", {"produtos": produtos, "q": q})


@proprietaria_required
def criar(request):
    form = ProdutoForm(request.POST or None)
    if form.is_valid():
        produto = form.save()
        messages.success(request, f"{produto.nome} cadastrado. Registre a reposição para dar saldo ao produto.")
        return redirect("catalogo:lista")
    return render(request, "catalogo/form.html", {"form": form, "titulo": "Novo produto"})


@proprietaria_required
def editar(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    form = ProdutoForm(request.POST or None, instance=produto)
    if form.is_valid():
        form.save()
        messages.success(request, f"{produto.nome} atualizado.")
        return redirect("catalogo:lista")
    return render(request, "catalogo/form.html", {"form": form, "titulo": f"Editar {produto.nome}"})


@proprietaria_required
@require_POST
def alternar_situacao(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    produto.ativo = not produto.ativo
    produto.save(update_fields=["ativo"])
    messages.success(request, f"{produto.nome} {'reativado' if produto.ativo else 'inativado'}.")
    return redirect("catalogo:lista")


@proprietaria_required
def excluir(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if not produto.pode_excluir:
        messages.error(request, "Este produto tem vendas ou movimentos no histórico. Inative-o em vez de excluir.")
        return redirect("catalogo:lista")
    if request.method == "POST":
        produto.delete()
        messages.success(request, f"{produto.nome} excluído.")
        return redirect("catalogo:lista")
    return render(request, "catalogo/confirmar_exclusao.html", {"produto": produto})
