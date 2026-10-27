from django import forms
from django.core.exceptions import ValidationError

from .utils import reais_para_centavos


class ReaisField(forms.Field):
    """Campo de formulário que recebe 'R$ 7,50' e entrega 750 (centavos)."""

    widget = forms.TextInput
    default_error_messages = {"invalid": "Informe um valor em reais, por exemplo 7,50."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.attrs.setdefault("inputmode", "decimal")
        self.widget.attrs.setdefault("placeholder", "0,00")

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            return reais_para_centavos(value)
        except ValueError:
            raise ValidationError(self.error_messages["invalid"], code="invalid")

    def validate(self, value):
        super().validate(value)
        if value is not None and value <= 0:
            raise ValidationError("O valor deve ser maior que zero.", code="min_value")
