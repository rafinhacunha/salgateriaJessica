# Salgateria da Jéssica — Sistema de vendas e estoque

Atividade de AEX — *Do modelo ao sistema web* · Programação para Internet (UENP, Campus Luiz Meneghel) + Engenharia de Software II.

**Integrantes:** Gabriel Ramos, Marcelo Sousa, Rafael Cunha

Sistema web que apoia o ponto de venda e o controle de estoque da Salgateria da Jéssica, implementado a partir da especificação de Engenharia de Software II (10 histórias de usuário, 16 requisitos funcionais, regras de negócio e diagramas UML).

## Tecnologias
- Python 3.10+ e Django 5.x
- SQLite (arquivo `db.sqlite3`, criado automaticamente; não exige instalar servidor de banco)
- HTML + CSS próprios (sem dependência externa, funciona offline)

## Como executar

```bash
# 1. (opcional) ambiente virtual
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. dependências
pip install -r requirements.txt

# 3. banco de dados
python manage.py migrate

# 4. dados de demonstração (usuários + 14 produtos com saldo)
python manage.py popular_demo

# 5. servidor
python manage.py runserver
```

Acesse <http://127.0.0.1:8000/>.

### Usuários de teste (senha `demo1234`)
| Login    | Perfil       | O que pode fazer |
|----------|--------------|------------------|
| `jessica`| Proprietária | Tudo: catálogo, reposição, ajuste, histórico, relatório, vendas. Também acessa `/admin/` para criar/ativar/inativar usuários |
| `carla`  | Atendente    | Buscar produtos, compor venda, registrar pagamento, comprovante, consultar estoque |

### Testes automatizados
```bash
python manage.py test      # 27 testes cobrindo as regras de negócio e o fluxo completo
```

## Estrutura do código (RNF10: módulos separados, regras centralizadas)

```
config/     configurações e rotas do projeto
nucleo/     base visual (template, CSS), formatação em R$, utilitários, comando popular_demo
contas/     Usuario (perfil Proprietária/Atendente), login e logout        -> RF01, RF02
catalogo/   Produto e CRUD do catálogo                                      -> RF03
estoque/    MovimentoEstoque, consulta, reposição, ajuste, histórico        -> RF13-RF15
            services.py: única porta de entrada para alterar saldo
vendas/     Venda, ItemVenda, Pagamento, busca, pedido, pagamento,
            comprovante, lista e relatório                                  -> RF04-RF12, RF16
            services.py: regras de venda, troco e conclusão transacional
```

## Telas (caminho principal do diagrama de atividades)
`/entrar/` login → `/` busca e pedido → `/venda/pagamento/` → `/venda/registro/` → `/venda/<id>/comprovante/`
Mais: `/vendas/` (lista), `/estoque/`, `/estoque/reposicao/`, `/estoque/ajuste/`, `/estoque/movimentos/`, `/catalogo/`, `/relatorio/`.

## Rastreabilidade com a especificação

| História | Onde está |
|---|---|
| HU01 Acessar o sistema | `contas` (conta inativa ou senha errada não inicia sessão) |
| HU02 Manter catálogo | `catalogo` (cadastrar, editar, inativar/reativar; excluir só sem histórico) |
| HU03 Buscar produtos | `vendas.views.nova_venda` (nome sem acento/maiúsculas + categoria; mensagem se nada for encontrado) |
| HU04 Compor venda e validar saldo | `vendas.services.adicionar_item` / `alterar_quantidade` |
| HU05 Total e preço preservado | `ItemVenda.preco_unitario_centavos`, `Venda.calcular_total` |
| HU06 Pagamento e troco | `vendas.services.definir_pagamento`, `calcular_troco` |
| HU07 Confirmar Pix/cartão | caixa de confirmação manual em `registro.html`; nenhum dado de cartão/Pix é pedido ou salvo |
| HU08 Concluir e comprovante | `vendas.services.concluir_venda`, `comprovante.html` |
| HU09 Reposição, ajuste e histórico | `estoque.services`, `estoque/movimentos` |
| HU10 Relatório de vendas | `vendas.services.relatorio`, `/relatorio/` |

Requisitos não funcionais atendidos de forma direta: valores em **centavos inteiros** (RNF03); conclusão da venda, pagamento e baixa em **uma única transação** (RNF04/RNF09); restrição de banco impedindo baixa duplicada do mesmo item de venda; permissões por perfil (RNF05); responsável e data/hora em cada movimento e venda (RNF06); interface em pt-BR, R$ e dd/mm/aaaa (RNF01).

## Decisões e limitações
- **Excluir produto:** a especificação prevê inativar (RN07). A exclusão definitiva só é permitida para produtos sem vendas nem movimentos (cadastro feito por engano).
- **Venda aberta:** cada atendente tem no máximo uma venda aberta, salva no banco; se a página for fechada, o pedido continua de onde parou. Se os itens mudarem, o pagamento informado é descartado e precisa ser refeito.
- **Produto repetido:** adicionar de novo o mesmo produto soma à quantidade já no pedido.
- **Fora do escopo (RN08):** cliente, venda on-line, entrega, desconto, pagamento dividido, devolução, cancelamento de venda e emissão fiscal. O comprovante diz "sem valor fiscal".
- **Backup (RNF08):** copie o arquivo `db.sqlite3` com o sistema parado; para restaurar, substitua o arquivo.
- **Produção:** defina `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` e `DJANGO_ALLOWED_HOSTS`.
