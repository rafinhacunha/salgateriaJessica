_SECOES = {
    "vendas:nova": "venda",
    "vendas:pagamento": "venda",
    "vendas:registro": "venda",
    "vendas:comprovante": "venda",
    "vendas:lista": "vendas",
    "vendas:relatorio": "relatorio",
}


def navegacao(request):
    """Informa ao template qual item do menu está ativo."""
    m = request.resolver_match
    if not m:
        return {}
    return {
        "secao": _SECOES.get(m.view_name, m.namespace),
        "etapas_venda": [(1, "Produtos"), (2, "Pagamento"), (3, "Registro"), (4, "Comprovante")],
    }
