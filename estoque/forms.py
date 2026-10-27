from django import forms

from catalogo.models import Produto


class _BaseMovimentoForm(forms.Form):
    produto = forms.ModelChoiceField(queryset=Produto.objects.none(), label="Produto", empty_label="Selecione o produto")
    motivo = forms.CharField(max_length=200, label="Motivo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["produto"].queryset = Produto.objects.order_by("-ativo", "nome")
        self.fields["produto"].label_from_instance = lambda p: f"{p.nome} (saldo {p.saldo})" + ("" if p.ativo else " - inativo")

    def clean_motivo(self):
        motivo = self.cleaned_data["motivo"].strip()
        if not motivo:
            raise forms.ValidationError("Informe o motivo.")
        return motivo


class EntradaForm(_BaseMovimentoForm):
    quantidade = forms.IntegerField(min_value=1, label="Quantidade recebida ou produzida")
    field_order = ["produto", "quantidade", "motivo"]


class AjusteForm(_BaseMovimentoForm):
    saldo_contado = forms.IntegerField(min_value=0, label="Saldo contado fisicamente")
    field_order = ["produto", "saldo_contado", "motivo"]
