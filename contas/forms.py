from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Login ou senha incorretos, ou conta inativa. Fale com a proprietária.",
        "inactive": "Conta inativa. Fale com a proprietária para ativar o seu usuário.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Login"
        self.fields["username"].widget.attrs.update({"autofocus": True, "autocomplete": "username"})
        self.fields["password"].widget = forms.PasswordInput(attrs={"autocomplete": "current-password"})
