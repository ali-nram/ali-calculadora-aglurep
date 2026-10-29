import re
import unicodedata
from decimal import Decimal, InvalidOperation
from .models import DomainError

def object_fields(value, expected, field="", record_id=""):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise DomainError("La estructura debe incluir exactamente: " + ", ".join(expected), field, record_id)
    return value

def number(value, field, record_id="", *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise DomainError("Ingrese un número decimal como texto, sin separadores de miles.", field, record_id)
    raw = str(value).strip()
    if len(raw) > 100 or not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", raw):
        raise DomainError("El número es demasiado largo.", field, record_id)
    try:
        result = Decimal(raw)
    except InvalidOperation:
        raise DomainError("Ingrese un número decimal válido.", field, record_id) from None
    if not result.is_finite():
        raise DomainError("El número debe ser finito.", field, record_id)
    if result < 0 or (positive and result == 0):
        raise DomainError("El valor debe ser mayor que cero." if positive else "El valor no puede ser negativo.", field, record_id)
    if result == 0:
        return Decimal(0)
    if result and (len(result.as_tuple().digits) > 28 or not -12 <= result.adjusted() <= 12):
        raise DomainError("Use hasta 28 cifras significativas y valores entre 1e-12 y menores de 1e13.", field, record_id)
    return result

def text(value, field, record_id=""):
    if not isinstance(value, str) or not value.strip():
        raise DomainError("Este campo de texto es obligatorio.", field, record_id)
    if len(value) > 250 or any(unicodedata.category(c) in {"Cc", "Zl", "Zp"} for c in value):
        raise DomainError("Use hasta 250 caracteres sin saltos de línea ni caracteres de control.", field, record_id)
    return value
