from django import forms

from nucleo.campos import ReaisField

from .models import Produto


class ProdutoForm(forms.ModelForm):
    preco = ReaisField(label="Preço (R$)")

    class Meta:
        model = Produto
        fields = ["nome", "categoria", "unidade"]
        labels = {"nome": "Nome", "categoria": "Categoria", "unidade": "Unidade vendável"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            from nucleo.utils import centavos_para_campo
            self.initial["preco"] = centavos_para_campo(self.instance.preco_centavos)
        self.order_fields(["nome", "categoria", "unidade", "preco"])

    def clean_nome(self):
        return self.cleaned_data["nome"].strip()

    def clean_categoria(self):
        return self.cleaned_data["categoria"].strip()

    def save(self, commit=True):
        self.instance.preco_centavos = self.cleaned_data["preco"]
        return super().save(commit)
