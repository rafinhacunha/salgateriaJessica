"""Funções de apoio: dinheiro sempre em centavos inteiros (RNF03)."""
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def reais_para_centavos(texto):
    """'7,50' -> 750 | '1.234,5' -> 123450 | '7.5' -> 750. Levanta ValueError se inválido."""
    t = str(texto).strip().replace("R$", "").replace(" ", "")
    if not t:
        raise ValueError("vazio")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(t)
    except InvalidOperation as exc:
        raise ValueError("inválido") from exc
    if not valor.is_finite() or valor != valor.quantize(Decimal("0.01")):
        raise ValueError("casas decimais")
    return int((valor * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def formatar_brl(centavos):
    """750 -> 'R$ 7,50'."""
    centavos = int(centavos or 0)
    reais, cent = divmod(abs(centavos), 100)
    inteiro = f"{reais:,}".replace(",", ".")
    return f"{'-' if centavos < 0 else ''}R$ {inteiro},{cent:02d}"


def centavos_para_campo(centavos):
    """750 -> '7,50' (valor inicial de campos de formulário)."""
    reais, cent = divmod(int(centavos), 100)
    return f"{reais},{cent:02d}"


def normalizar(texto):
    """Minúsculas e sem acentos, para busca tolerante ('pao' encontra 'Pão')."""
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).casefold()
