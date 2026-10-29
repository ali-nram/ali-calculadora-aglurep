from dataclasses import replace
from decimal import Decimal as D
import pytest
from app.domain.models import Composition
from app.services.validation_service import ValidationService

def composition(values):
    return Composition((object(),), D("100"), {p: D(v) for p, v in values.items()}, {p: D(v) for p, v in values.items()})

def test_target_complies(config):
    assert ValidationService().validate(composition({"PET":"9.5","PE":"83.5","PA":"4","EVOH":"3"}), config).status == "CUMPLE"

@pytest.mark.parametrize("pet,expected", [("10", "CUMPLE"), ("10.0000000000001", "NO CUMPLE"), ("10.1", "NO CUMPLE")])
def test_pet_hard_limit(config, pet, expected):
    values = {"PET":pet, "PE":"83", "PA":"4", "EVOH":"3"}
    criteria = ValidationService().validate(composition(values), config).criteria
    assert next(c for c in criteria if c.polymer == "PET").status == expected

@pytest.mark.parametrize("polymer,value", [("PE","78.5"),("PE","88.5"),("PA","0"),("PA","9"),("EVOH","0"),("EVOH","8")])
def test_inclusive_bounds(config, polymer, value):
    values = {"PET":"9.5","PE":"83.5","PA":"4","EVOH":"3"}
    values[polymer] = value
    criterion = next(c for c in ValidationService().validate(composition(values), config).criteria if c.polymer == polymer)
    assert criterion.status == "CUMPLE"

@pytest.mark.parametrize("polymer,value", [("PE","78.49999999"),("PE","88.50000001"),("PA","9.000001"),("EVOH","8.000001")])
def test_individual_failures(config, polymer, value):
    values = {"PET":"9.5","PE":"83.5","PA":"4","EVOH":"3"}
    values[polymer] = value
    result = ValidationService().validate(composition(values), config)
    assert result.status == "NO CUMPLE"
    criterion = next(c for c in result.criteria if c.polymer == polymer)
    assert criterion.status == "NO CUMPLE"
    assert criterion.explanation != "Dentro del intervalo permitido."

def test_empty_has_no_results(config):
    assert ValidationService().validate(None, config).status == "SIN RESULTADOS"
    assert ValidationService().validate(Composition((), D(0), {}, {}), config).status == "SIN RESULTADOS"
