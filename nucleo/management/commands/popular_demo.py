"""Cria usuários de teste e produtos de exemplo (pode ser executado várias vezes)."""
from django.core.management.base import BaseCommand
from django.db import transaction

from catalogo.models import Produto
from contas.models import Usuario
from estoque import services as estoque

SENHA = "demo1234"
USUARIOS = [
    ("jessica", "Jéssica", Usuario.Perfil.PROPRIETARIA),
    ("carla", "Carla", Usuario.Perfil.ATENDENTE),
]
PRODUTOS = [  # nome, categoria, unidade, preço em centavos, saldo inicial
    ("Coxinha de frango", "Fritos", "unidade", 750, 42),
    ("Coxinha de frango com catupiry", "Fritos", "unidade", 850, 18),
    ("Mini coxinha (pacote com 25)", "Pacotes", "pacote", 3200, 0),
    ("Pastel de carne", "Fritos", "unidade", 800, 30),
    ("Pastel de queijo", "Fritos", "unidade", 800, 25),
    ("Kibe", "Fritos", "unidade", 750, 20),
    ("Risole de presunto e queijo", "Fritos", "unidade", 750, 22),
    ("Empada de frango", "Assados", "unidade", 700, 20),
    ("Esfiha de carne", "Assados", "unidade", 700, 15),
    ("Pão de queijo", "Assados", "unidade", 400, 50),
    ("Refrigerante lata", "Bebidas", "unidade", 600, 36),
    ("Suco de laranja 300 ml", "Bebidas", "copo", 500, 12),
    ("Água mineral", "Bebidas", "unidade", 300, 40),
    ("Pacote de salgados mistos (50)", "Pacotes", "pacote", 6500, 8),
]


class Command(BaseCommand):
    help = "Cria usuários e produtos de demonstração."

    @transaction.atomic
    def handle(self, *args, **opcoes):
        donos = {}
        for login, nome, perfil in USUARIOS:
            u, criado = Usuario.objects.get_or_create(username=login, defaults={"first_name": nome, "perfil": perfil})
            if criado:
                u.set_password(SENHA)
                u.is_staff = u.is_superuser = perfil == Usuario.Perfil.PROPRIETARIA  # acesso ao /admin
                u.save()
            donos[perfil] = u
        for nome, cat, unidade, preco, saldo in PRODUTOS:
            p, criado = Produto.objects.get_or_create(
                nome=nome, defaults={"categoria": cat, "unidade": unidade, "preco_centavos": preco}
            )
            if criado and saldo:
                estoque.registrar_entrada(p.pk, saldo, "Saldo inicial (demonstração)", donos[Usuario.Perfil.PROPRIETARIA])
        self.stdout.write(self.style.SUCCESS(
            f"Pronto. Usuários: jessica (proprietária) e carla (atendente). Senha: {SENHA}"))
