from django.test import TestCase
from django.urls import reverse

from catalogo.models import Produto
from contas.models import Usuario
from estoque import services as estoque
from estoque.models import MovimentoEstoque
from nucleo.utils import formatar_brl, reais_para_centavos

from . import services
from .models import Pagamento, Venda


class BaseTeste(TestCase):
    def setUp(self):
        self.dona = Usuario.objects.create_user("jessica", password="x12345678", first_name="Jéssica", perfil="PROPRIETARIA")
        self.atendente = Usuario.objects.create_user("carla", password="x12345678", first_name="Carla", perfil="ATENDENTE")
        self.coxinha = Produto.objects.create(nome="Coxinha de frango", categoria="Fritos", preco_centavos=750)
        self.pastel = Produto.objects.create(nome="Pastel de carne", categoria="Fritos", preco_centavos=800)
        self.refri = Produto.objects.create(nome="Refrigerante lata", categoria="Bebidas", preco_centavos=600)
        for p, q in ((self.coxinha, 42), (self.pastel, 30), (self.refri, 36)):
            estoque.registrar_entrada(p.pk, q, "Saldo inicial", self.dona)

    def venda_exemplo(self):
        venda = services.obter_venda_aberta(self.atendente)
        services.adicionar_item(venda, self.coxinha.pk, 3)
        services.adicionar_item(venda, self.pastel.pk, 2)
        services.adicionar_item(venda, self.refri.pk, 1)
        return venda


class RegrasDeVendaTest(BaseTeste):
    def test_total_e_subtotais_em_centavos(self):  # HU05 / RF07
        venda = self.venda_exemplo()
        self.assertEqual(venda.total_centavos, 3 * 750 + 2 * 800 + 600)  # R$ 44,50

    def test_repetir_produto_atualiza_quantidade(self):  # HU04
        venda = self.venda_exemplo()
        services.adicionar_item(venda, self.coxinha.pk, 2)
        self.assertEqual(venda.itens.get(produto=self.coxinha).quantidade, 5)
        self.assertEqual(venda.itens.count(), 3)

    def test_quantidade_acima_do_saldo_e_bloqueada(self):  # HU04 / RF06
        venda = services.obter_venda_aberta(self.atendente)
        with self.assertRaisesMessage(services.ErroVenda, "restam 42"):
            services.adicionar_item(venda, self.coxinha.pk, 43)
        self.assertFalse(venda.itens.exists())

    def test_produto_inativo_ou_sem_saldo_nao_vende(self):  # RN07
        venda = services.obter_venda_aberta(self.atendente)
        self.pastel.ativo = False
        self.pastel.save()
        with self.assertRaises(services.ErroVenda):
            services.adicionar_item(venda, self.pastel.pk, 1)
        vazio = Produto.objects.create(nome="Kibe", categoria="Fritos", preco_centavos=700)
        with self.assertRaisesMessage(services.ErroVenda, "sem saldo"):
            services.adicionar_item(venda, vazio.pk, 1)

    def test_quantidade_deve_ser_positiva(self):
        venda = services.obter_venda_aberta(self.atendente)
        with self.assertRaises(services.ErroVenda):
            services.adicionar_item(venda, self.coxinha.pk, 0)

    def test_preco_preservado_apos_mudanca_no_catalogo(self):  # RN05
        venda = self.venda_exemplo()
        services.definir_pagamento(venda, "DINHEIRO", 5000)
        services.concluir_venda(venda.pk, self.atendente)
        self.coxinha.preco_centavos = 999
        self.coxinha.save()
        venda.refresh_from_db()
        self.assertEqual(venda.total_centavos, 4450)
        self.assertEqual(venda.itens.get(produto=self.coxinha).preco_unitario_centavos, 750)


class PagamentoTest(BaseTeste):
    def test_troco_exato(self):  # HU06 / RN03
        venda = self.venda_exemplo()
        pag = services.definir_pagamento(venda, "DINHEIRO", 5000)
        self.assertEqual(pag.troco_centavos, 550)

    def test_valor_menor_que_total_impede(self):
        venda = self.venda_exemplo()
        with self.assertRaises(services.ErroVenda):
            services.definir_pagamento(venda, "DINHEIRO", 4000)

    def test_pix_nao_tem_troco_nem_valor(self):
        venda = self.venda_exemplo()
        pag = services.definir_pagamento(venda, "PIX")
        self.assertIsNone(pag.valor_recebido_centavos)
        self.assertEqual(pag.troco_centavos, 0)
        self.assertFalse(pag.confirmado)

    def test_um_meio_por_venda(self):  # RN02
        venda = self.venda_exemplo()
        services.definir_pagamento(venda, "PIX")
        services.definir_pagamento(venda, "CARTAO")
        self.assertEqual(Pagamento.objects.filter(venda=venda).count(), 1)
        self.assertEqual(Pagamento.objects.get(venda=venda).meio, "CARTAO")


class ConclusaoTest(BaseTeste):
    def test_conclusao_baixa_estoque_uma_vez(self):  # HU08 / RN06 / RNF09
        venda = self.venda_exemplo()
        services.definir_pagamento(venda, "DINHEIRO", 5000)
        services.concluir_venda(venda.pk, self.atendente)
        self.coxinha.refresh_from_db()
        self.assertEqual(self.coxinha.saldo, 39)
        mov = MovimentoEstoque.objects.get(venda=venda, produto=self.coxinha)
        self.assertEqual((mov.tipo, mov.quantidade, mov.saldo_anterior, mov.saldo_posterior), ("SAIDA", -3, 42, 39))
        with self.assertRaises(services.ErroVenda):
            services.concluir_venda(venda.pk, self.atendente)
        self.coxinha.refresh_from_db()
        self.assertEqual(self.coxinha.saldo, 39)
        self.assertEqual(MovimentoEstoque.objects.filter(venda=venda).count(), 3)

    def test_venda_sem_item_ou_sem_pagamento_nao_conclui(self):
        venda = services.obter_venda_aberta(self.atendente)
        with self.assertRaises(services.ErroVenda):
            services.concluir_venda(venda.pk, self.atendente)
        services.adicionar_item(venda, self.coxinha.pk, 1)
        with self.assertRaises(services.ErroVenda):
            services.concluir_venda(venda.pk, self.atendente)

    def test_falha_nao_deixa_baixa_parcial(self):  # RNF04
        venda = self.venda_exemplo()
        services.definir_pagamento(venda, "DINHEIRO", 5000)
        self.refri.saldo = 0  # simula alguém esgotando o produto antes da conclusão
        self.refri.save()
        with self.assertRaises(services.ErroVenda):
            services.concluir_venda(venda.pk, self.atendente)
        self.coxinha.refresh_from_db()
        self.assertEqual(self.coxinha.saldo, 42)
        venda.refresh_from_db()
        self.assertEqual(venda.situacao, Venda.Situacao.ABERTA)

    def test_relatorio_separa_por_pagamento(self):  # HU10
        v1 = self.venda_exemplo()
        services.definir_pagamento(v1, "DINHEIRO", 5000)
        services.concluir_venda(v1.pk, self.atendente)
        v2 = services.obter_venda_aberta(self.atendente)
        services.adicionar_item(v2, self.refri.pk, 2)
        services.definir_pagamento(v2, "PIX")
        services.concluir_venda(v2.pk, self.atendente)
        hoje = services.periodo_padrao()
        r = services.relatorio(*hoje)
        por = {m["rotulo"]: m for m in r["por_meio"]}
        self.assertEqual((r["quantidade"], r["total"]), (2, 4450 + 1200))
        self.assertEqual(por["Dinheiro"]["total"], 4450)
        self.assertEqual(por["Pix"]["quantidade"], 1)
        self.assertEqual(por["Cartão"]["quantidade"], 0)


class EstoqueTest(BaseTeste):
    def test_entrada_e_ajuste_com_historico(self):  # HU09
        estoque.registrar_entrada(self.coxinha.pk, 10, "Produção do dia", self.dona)
        self.coxinha.refresh_from_db()
        self.assertEqual(self.coxinha.saldo, 52)
        mov = estoque.registrar_ajuste(self.coxinha.pk, 50, "Contagem física", self.dona)
        self.assertEqual((mov.saldo_anterior, mov.saldo_posterior, mov.quantidade), (52, 50, -2))
        self.assertEqual(mov.tipo, "AJUSTE")

    def test_ajuste_exige_motivo_e_nao_fica_negativo(self):
        with self.assertRaises(estoque.ErroEstoque):
            estoque.registrar_ajuste(self.coxinha.pk, 10, "  ", self.dona)
        with self.assertRaises(estoque.ErroEstoque):
            estoque.registrar_ajuste(self.coxinha.pk, -1, "erro", self.dona)


class AcessoTest(BaseTeste):
    def test_exige_login(self):
        r = self.client.get(reverse("vendas:nova"))
        self.assertRedirects(r, f"{reverse('contas:login')}?next=/")

    def test_login_conta_inativa_falha(self):  # HU01
        self.atendente.is_active = False
        self.atendente.save()
        r = self.client.post(reverse("contas:login"), {"username": "carla", "password": "x12345678"})
        self.assertContains(r, "conta inativa")
        r = self.client.get(reverse("vendas:nova"))
        self.assertEqual(r.status_code, 302)

    def test_atendente_nao_acessa_areas_da_proprietaria(self):  # RF02
        self.client.login(username="carla", password="x12345678")
        for nome in ("catalogo:lista", "catalogo:criar", "estoque:reposicao", "estoque:ajuste", "estoque:movimentos", "vendas:relatorio"):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 403, nome)
        self.assertEqual(self.client.get(reverse("estoque:consulta")).status_code, 200)

    def test_proprietaria_acessa_tudo(self):
        self.client.login(username="jessica", password="x12345678")
        for nome in ("catalogo:lista", "catalogo:criar", "estoque:reposicao", "estoque:ajuste", "estoque:movimentos", "vendas:relatorio"):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 200, nome)


class FluxoWebTest(BaseTeste):
    def test_fluxo_completo_dinheiro_pelo_navegador(self):
        c = self.client
        c.login(username="carla", password="x12345678")
        r = c.get(reverse("vendas:nova"), {"q": "pao", "categoria": ""})
        self.assertContains(r, "Não encontramos produtos")
        r = c.get(reverse("vendas:nova"), {"q": "COXINHA", "categoria": ""})
        self.assertContains(r, "Coxinha de frango")
        c.post(reverse("vendas:adicionar"), {"produto": self.coxinha.pk, "quantidade": 3})
        c.post(reverse("vendas:adicionar"), {"produto": self.pastel.pk, "quantidade": 2})
        c.post(reverse("vendas:adicionar"), {"produto": self.refri.pk, "quantidade": 1})
        r = c.get(reverse("vendas:pagamento"))
        self.assertContains(r, "R$ 44,50")
        r = c.post(reverse("vendas:pagamento"), {"meio": "DINHEIRO", "valor_recebido": "40,00"})
        self.assertContains(r, "menor que o total")
        r = c.post(reverse("vendas:pagamento"), {"meio": "DINHEIRO", "valor_recebido": "50,00"})
        self.assertRedirects(r, reverse("vendas:registro"))
        self.assertContains(c.get(reverse("vendas:registro")), "R$ 5,50")
        venda = Venda.objects.get(usuario=self.atendente)
        r = c.post(reverse("vendas:registro"))
        self.assertRedirects(r, reverse("vendas:comprovante", args=[venda.pk]))
        r = c.get(reverse("vendas:comprovante", args=[venda.pk]))
        self.assertContains(r, "Venda registrada")
        self.assertContains(r, venda.identificador)
        self.assertContains(r, "R$ 44,50")

    def test_pix_exige_confirmacao_manual(self):
        c = self.client
        c.login(username="carla", password="x12345678")
        c.post(reverse("vendas:adicionar"), {"produto": self.refri.pk, "quantidade": 1})
        c.post(reverse("vendas:pagamento"), {"meio": "PIX"})
        c.post(reverse("vendas:registro"))
        self.assertEqual(Venda.objects.get().situacao, "ABERTA")
        c.post(reverse("vendas:registro"), {"confirmo": "on"})
        self.assertEqual(Venda.objects.get().situacao, "CONCLUIDA")

    def test_atendente_so_ve_comprovante_proprio(self):
        venda = self.venda_exemplo()
        services.definir_pagamento(venda, "PIX")
        services.concluir_venda(venda.pk, self.atendente)
        outra = Usuario.objects.create_user("ana", password="x12345678", perfil="ATENDENTE")
        self.client.force_login(outra)
        self.assertEqual(self.client.get(reverse("vendas:comprovante", args=[venda.pk])).status_code, 403)
        self.client.force_login(self.dona)
        self.assertEqual(self.client.get(reverse("vendas:comprovante", args=[venda.pk])).status_code, 200)


class UtilsTest(TestCase):
    def test_conversoes(self):
        self.assertEqual(reais_para_centavos("7,50"), 750)
        self.assertEqual(reais_para_centavos("R$ 1.234,5"), 123450)
        self.assertEqual(reais_para_centavos("50"), 5000)
        for ruim in ("abc", "1,234", ""):
            with self.assertRaises(ValueError):
                reais_para_centavos(ruim)
        self.assertEqual(formatar_brl(4450), "R$ 44,50")
        self.assertEqual(formatar_brl(123456), "R$ 1.234,56")
