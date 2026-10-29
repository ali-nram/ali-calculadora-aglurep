"""Contratos de dominio independientes de Flask; todas las magnitudes usan Decimal."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

POLYMERS = ("PET", "PE", "PA", "EVOH")
LAYERS = ("PET", "PA", "EVOH")
VERSION = "1.0.0"
METHOD = "Aglurep-v1-masa-espesor-densidad/1"

class DomainError(ValueError):
    def __init__(self, message: str, field: str = "", record_id: str = "", code: str = "invalid_data"):
        super().__init__(message)
        self.message, self.field, self.record_id, self.code = message, field, record_id, code

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "field": self.field, "record_id": self.record_id}

@dataclass(frozen=True)
class TechnicalConfiguration:
    densities: dict[str, Decimal]
    default_thicknesses: dict[str, Decimal]
    targets: dict[str, Decimal]
    tolerances: dict[str, Decimal]
    pet_limit: Decimal

@dataclass(frozen=True)
class Laminate:
    record_id: str
    erp_id: str
    material: str
    total_thickness_um: Decimal
    mass_kg: Decimal
    thicknesses: dict[str, Decimal]

@dataclass(frozen=True)
class LaminateResult:
    laminate: Laminate
    thicknesses: dict[str, Decimal]
    contributions: dict[str, Decimal]
    fractions: dict[str, Decimal]
    masses_kg: dict[str, Decimal]

@dataclass(frozen=True)
class Composition:
    laminates: tuple[LaminateResult, ...]
    total_mass_kg: Decimal
    masses_kg: dict[str, Decimal]
    percentages: dict[str, Decimal]

@dataclass(frozen=True)
class Criterion:
    polymer: str
    value: Decimal
    target: Decimal
    minimum: Decimal
    maximum: Decimal
    difference: Decimal
    status: str
    explanation: str

@dataclass(frozen=True)
class Validation:
    status: str
    criteria: tuple[Criterion, ...]

@dataclass(frozen=True)
class Calculation:
    calculation_id: str
    configuration: TechnicalConfiguration
    configuration_profile: str
    composition: Composition
    validation: Validation
    aglurep_id: str

def wire(value: Any) -> Any:
    """Serialización sin conversión a float ni redondeos de presentación."""
    from dataclasses import fields, is_dataclass
    if isinstance(value, Decimal):
        return format(value, "f")
    if is_dataclass(value):
        return {f.name: wire(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {k: wire(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [wire(v) for v in value]
    return value
