from copy import deepcopy
from decimal import Decimal as D
import pytest
from app.domain.models import DomainError, wire
from app.services.laminate_service import LaminateService
from app.services.composition_service import CompositionService
from app.services.configuration_service import ConfigurationService

def test_create_unique_ids_and_defaults(config):
    service = LaminateService()
    a, b = service.create(config), service.create(config)
    assert a["record_id"] != b["record_id"]
    assert a["thicknesses"] == {"PET":"10", "PA":"12", "EVOH":"3"}
    assert a["erp_id"] == "" and a["material"] == ""

def test_edit_preserves_identity_and_custom_layers(row, config):
    service = LaminateService()
    rows = service.selected([row])
    edited = service.edit(rows, row["record_id"], {"thicknesses":{"PET":"5.25","PA":"0","EVOH":"1.125"}, "material":"Otra referencia"})
    edited = service.edit(edited, row["record_id"], {"mass_kg":"35"})
    assert edited[0].record_id == row["record_id"]
    assert edited[0].erp_id == row["erp_id"]
    assert edited[0].material == "Otra referencia"
    assert edited[0].thicknesses["PET"] == D("5.25")
    assert edited[0].thicknesses["EVOH"] == D("1.125")
    assert CompositionService().calculate(edited, config).total_mass_kg == D("35")
    assert CompositionService().calculate(rows, config).total_mass_kg == D("20")

def test_duplicate_erp_different_materials_and_removal(row, config):
    service = LaminateService()
    second = deepcopy(row)
    second.update(record_id="00000000-0000-4000-8000-000000000002", material="PET/Flexible", mass_kg="5")
    rows = service.selected([row,second])
    assert rows[0].erp_id == rows[1].erp_id
    before = CompositionService().calculate(rows, config)
    after = CompositionService().calculate(service.remove(rows, second["record_id"]), config)
    assert before.total_mass_kg == D("25")
    assert after.total_mass_kg == D("20")
    assert len(after.laminates) == 1
    assert abs(sum(after.masses_kg.values()) - 20) < D("1e-25")
    assert abs(sum(after.percentages.values()) - 100) < D("1e-25")

def test_duplicate_record_rejected(row):
    with pytest.raises(DomainError, match="únicos"):
        LaminateService().selected([row,deepcopy(row)])

@pytest.mark.parametrize("field,value", [("mass_kg","0"),("mass_kg","-1"),("mass_kg","NaN"),("mass_kg","Infinity"),
    ("mass_kg",True),("mass_kg",1.5),("mass_kg",None),("mass_kg","abc"),("mass_kg","1e9999"),
    ("total_thickness_um","0"),("total_thickness_um","24"),("erp_id",""),("erp_id",None),("material","  "),
    ("record_id","not-a-uuid"),("record_id",None),("record_id",True)])
def test_invalid_fields(row, field, value):
    row[field] = value
    with pytest.raises(DomainError):
        LaminateService().selected([row])

def test_absent_and_extra_fields(row):
    row.pop("mass_kg")
    with pytest.raises(DomainError): LaminateService().selected([row])
    row["unsupported"] = "value"
    with pytest.raises(DomainError): LaminateService().selected([row])

@pytest.mark.parametrize("value", ["-0.1","NaN",None,"bad"])
def test_invalid_layers(row, value):
    row["thicknesses"]["PET"] = value
    with pytest.raises(DomainError): LaminateService().selected([row])

@pytest.mark.parametrize("operation", ["edit", "remove"])
def test_missing_record(row, operation):
    service = LaminateService()
    with pytest.raises(DomainError):
        getattr(service, operation)(service.selected([row]), "missing", *([{}] if operation == "edit" else []))

def test_id_cannot_be_edited(row):
    service = LaminateService()
    with pytest.raises(DomainError):
        service.edit(service.selected([row]), row["record_id"], {"record_id":row["record_id"]})

@pytest.mark.parametrize("value", ["0","-1","NaN","Infinity","bad",None,True])
def test_invalid_density(config, value):
    data = wire(config); data["densities"]["PET"] = value
    with pytest.raises(DomainError): ConfigurationService().validate(data)

def test_missing_config_parameter(config):
    data = wire(config); del data["densities"]["PE"]
    with pytest.raises(DomainError): ConfigurationService().validate(data)

@pytest.mark.parametrize("mutation", ["target_sum","target_range","negative_tolerance","pet_limit","missing","extra_polymer"])
def test_invalid_configuration(config, mutation):
    data = wire(config)
    if mutation == "target_sum": data["targets"]["PE"] = "82"
    if mutation == "target_range": data["targets"]["PE"] = "101"
    if mutation == "negative_tolerance": data["tolerances"]["PA"] = "-1"
    if mutation == "pet_limit": data["pet_limit"] = "9"
    if mutation == "missing": data.pop("targets")
    if mutation == "extra_polymer": data["densities"]["PP"] = "900"
    with pytest.raises(DomainError): ConfigurationService().validate(data)

def test_custom_configuration(config):
    service = ConfigurationService()
    data = wire(config)
    data["densities"]["PE"] = "950"
    data["default_thicknesses"]["PA"] = "0"
    data["targets"]["PE"] = "84"; data["targets"]["PA"] = "3.5"
    data["tolerances"]["PA"] = "4"
    custom = service.validate(data)
    assert service.profile(custom) == "Personalizada"
    assert service.profile(service.validate(wire(config))) == "Aglurep v1"
    assert LaminateService().create(custom)["thicknesses"]["PA"] == "0"

def test_defensive_zero_contributions(row, config):
    from dataclasses import replace
    bad = replace(config, densities={p:D(0) for p in config.densities})
    with pytest.raises(DomainError, match="contribuciones"):
        CompositionService().calculate(LaminateService().selected([row]), bad)

@pytest.mark.parametrize("value", ["1_000", "1,000", "0x10", "1e-99999", "1e99999"])
def test_numeric_syntax_and_magnitude(row, value):
    row["mass_kg"] = value
    with pytest.raises(DomainError): LaminateService().selected([row])

def test_zero_exponent_is_canonicalized(row):
    row["thicknesses"]["PA"] = "0e-999999999"
    assert wire(LaminateService().selected([row]))[0]["thicknesses"]["PA"] == "0"

@pytest.mark.parametrize("control", ["\n", "\t", "\x7f", "\u0085", "\u2028"])
def test_text_control_characters_rejected(row, control):
    row["material"] = "PET" + control + "HBA"
    with pytest.raises(DomainError): LaminateService().selected([row])

def test_collection_limit_and_type(row):
    with pytest.raises(DomainError): LaminateService().selected([row] * 501)
    with pytest.raises(DomainError): LaminateService().selected({"row":row})
