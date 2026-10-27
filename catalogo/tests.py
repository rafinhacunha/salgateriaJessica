from django.test import TestCase
from django.urls import reverse

from catalogo.models import Produto
from contas.models import Usuario
from estoque import services as estoque


class CatalogoTest(TestCase):
    def setUp(self):
        self.dona = Usuario.objects.create_user("jessica", password="x12345678", perfil="PROPRIETARIA")
        self.client.force_login(self.dona)

    def test_crud_completo(self):  # HU02
        r = self.client.post(reverse("catalogo:criar"), {"nome": "Kibe", "categoria": "Fritos", "unidade": "unidade", "preco": "7,50"})
        self.assertRedirects(r, reverse("catalogo:lista"))
        p = Produto.objects.get(nome="Kibe")
        self.assertEqual(p.preco_centavos, 750)
        self.client.post(reverse("catalogo:editar", args=[p.pk]), {"nome": "Kibe", "categoria": "Fritos", "unidade": "unidade", "preco": "8,00"})
        p.refresh_from_db()
        self.assertEqual(p.preco_centavos, 800)
        self.client.post(reverse("catalogo:situacao", args=[p.pk]))
        p.refresh_from_db()
        self.assertFalse(p.ativo)
        self.client.post(reverse("catalogo:excluir", args=[p.pk]))
        self.assertFalse(Produto.objects.filter(pk=p.pk).exists())

    def test_preco_obrigatorio_e_maior_que_zero(self):
        for preco in ("0", "-1", "", "abc"):
            r = self.client.post(reverse("catalogo:criar"), {"nome": "X", "categoria": "Y", "unidade": "unidade", "preco": preco})
            self.assertEqual(r.status_code, 200, preco)
        self.assertEqual(Produto.objects.count(), 0)

    def test_produto_com_historico_nao_exclui(self):
        p = Produto.objects.create(nome="Kibe", categoria="Fritos", preco_centavos=750)
        estoque.registrar_entrada(p.pk, 5, "inicial", self.dona)
        self.client.post(reverse("catalogo:excluir", args=[p.pk]))
        self.assertTrue(Produto.objects.filter(pk=p.pk).exists())
