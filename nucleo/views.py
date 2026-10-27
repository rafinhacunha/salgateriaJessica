from django.shortcuts import render


def acesso_negado(request, exception=None):
    return render(request, "403.html", status=403)
