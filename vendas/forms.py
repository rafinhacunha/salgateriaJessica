from django import forms

from nucleo.campos import ReaisField

from .models import Pagamento


class PagamentoForm(forms.Form):
    meio = forms.ChoiceField(choices=Pagamento.Meio.choices, error_messages={"required": "Escolha a forma de pagamento."})
    valor_recebido = ReaisField(required=False, label="Valor recebido do cliente")

    def __init__(self, *args, total_centavos=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_centavos = total_centavos

    def clean(self):
        dados = super().clean()
        if dados.get("meio") == Pagamento.Meio.DINHEIRO and not self.has_error("valor_recebido"):
            valor = dados.get("valor_recebido")
            if valor is None:
                self.add_error("valor_recebido", "Informe o valor recebido.")
            elif valor < self.total_centavos:
                self.add_error("valor_recebido", "O valor recebido é menor que o total da venda.")
        return dados


class PeriodoForm(forms.Form):
    inicio = forms.DateField(label="De", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    fim = forms.DateField(label="Até", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))

    def clean(self):
        dados = super().clean()
        if dados.get("inicio") and dados.get("fim") and dados["inicio"] > dados["fim"]:
            raise forms.ValidationError("A data inicial não pode ser posterior à data final.")
        return dados
