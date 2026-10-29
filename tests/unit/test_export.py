import csv
import io
import json
from copy import deepcopy
from decimal import Decimal as D, ROUND_HALF_UP
from dataclasses import replace
from uuid import UUID
import pytest
from app.services.calculation_service import CalculationService
from app.services.configuration_service import ConfigurationService
from app.services.laminate_service import LaminateService
from app.services.composition_service import CompositionService
from app.services.validation_service import ValidationService
from app.services.export_service import ExportService
from app.domain.models import POLYMERS, DomainError

def calculate(payload):
    return CalculationService(ConfigurationService(), LaminateService(), CompositionService(), ValidationService()).calculate(payload)[0]

def read_csv(content):
    return list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))

def test_summary_schema_and_backend_values(payload):
    result = calculate(payload)
    content = ExportService().export(result)
    assert content.startswith(b"\xef\xbb\xbf")
    rows = read_csv(content)
    assert len(rows) == 1
    row = rows[0]
    assert list(row) == ["id_aglurep", "cantidad_laminados", "partes_laminados_ERP", "estado_global",
                         "masa_PET_kg", "masa_PE_kg", "masa_PA_kg", "masa_EVOH_kg",
                         "porcentaje_PET", "porcentaje_PE", "porcentaje_PA", "porcentaje_EVOH", "perfil_configuracion"]
    assert row["id_aglurep"] == result.aglurep_id
    assert UUID(result.aglurep_id.removeprefix("AGL-"))
    assert result.aglurep_id != result.calculation_id
    assert row["cantidad_laminados"] == "1"
    assert json.loads(row["partes_laminados_ERP"]) == ["000123"]
    assert row["estado_global"] == result.validation.status
    for p in POLYMERS:
        assert row[f"masa_{p}_kg"] == format(result.composition.masses_kg[p].quantize(D("0.01"), rounding=ROUND_HALF_UP), ".2f")
        assert row[f"porcentaje_{p}"] == format(result.composition.percentages[p].quantize(D("0.01"), rounding=ROUND_HALF_UP), ".2f")

def test_two_laminates_one_summary_row_with_repeated_parts(payload):
    second = deepcopy(payload["laminates"][0])
    second["record_id"] = "00000000-0000-4000-8000-000000000002"
    second["mass_kg"] = "5"
    payload["laminates"].append(second)
    result = calculate(payload)
    rows = read_csv(ExportService().export(result))
    assert len(rows) == 1
    assert rows[0]["cantidad_laminados"] == "2"
    assert json.loads(rows[0]["partes_laminados_ERP"]) == ["000123", "000123"]
    assert abs(sum(D(rows[0][f"masa_{p}_kg"]) for p in POLYMERS) - D("25")) <= D("0.02")

@pytest.mark.parametrize("part", ['=SUM(1,2)', '+123', '-123', '@SUM(A1)', "'original", '000123', 'Niño, lámina; [A] "B"'])
def test_part_list_round_trip_and_formula_safety(payload, part):
    payload["laminates"][0]["erp_id"] = part
    row = read_csv(ExportService().export(calculate(payload)))[0]
    assert row["partes_laminados_ERP"].startswith("[")
    assert json.loads(row["partes_laminados_ERP"]) == [part]

def test_product_identity_is_new_for_each_calculation(payload):
    a, b = calculate(payload), calculate(payload)
    assert a.aglurep_id != b.aglurep_id
    assert ExportService().export(a) == ExportService().export(a)

def test_empty_mix_cannot_export(payload):
    result = calculate(payload)
    empty = replace(result, composition=replace(result.composition, laminates=()))
    with pytest.raises(DomainError):
        ExportService().export(empty)

@pytest.mark.parametrize("mass,expected", [("1.005","1.01"),("0.001","0.00"),("2","2.00")])
def test_csv_two_decimals_only_at_export(payload, mass, expected):
    payload["laminates"][0]["mass_kg"] = mass
    payload["laminates"][0]["thicknesses"] = {"PET":"0","PA":"0","EVOH":"0"}
    result = calculate(payload)
    before = dict(result.composition.masses_kg)
    row = read_csv(ExportService().export(result))[0]
    assert row["masa_PE_kg"] == expected
    assert row["porcentaje_PE"] == "100.00"
    assert row["masa_PET_kg"] == "0.00"
    assert row["porcentaje_PET"] == "0.00"
    assert result.composition.masses_kg == before
    assert result.composition.masses_kg["PE"] == D(mass)

def test_rounding_never_changes_pet_evaluation(payload):
    payload["laminates"] = []
    for index,(p,mass) in enumerate((("PET","10.001"),("PE","82.999"),("PA","4"),("EVOH","3")),1):
        payload["laminates"].append({"record_id":f"00000000-0000-4000-8000-{index:012d}","erp_id":p,"material":p,
            "mass_kg":mass,"total_thickness_um":"100","thicknesses":{q:"100" if p==q else "0" for q in ("PET","PA","EVOH")}})
    result = calculate(payload)
    row = read_csv(ExportService().export(result))[0]
    assert row["porcentaje_PET"] == "10.00"
    assert row["estado_global"] == "NO CUMPLE"
    assert result.composition.percentages["PET"] == D("10.001")
