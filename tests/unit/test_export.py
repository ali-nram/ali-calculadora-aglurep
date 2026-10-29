import csv
import io
from datetime import datetime
from decimal import Decimal as D
from zoneinfo import ZoneInfo
from app.services.calculation_service import CalculationService
from app.services.configuration_service import ConfigurationService
from app.services.laminate_service import LaminateService
from app.services.composition_service import CompositionService
from app.services.validation_service import ValidationService
from app.services.export_service import ExportService
from app.domain.models import POLYMERS

def test_csv_all_values_and_reversible_text(payload):
    payload["laminates"][0]["erp_id"] = "000123"
    payload["laminates"][0]["material"] = "=SUM(1,2) · Niño, lámina española"
    service = CalculationService(ConfigurationService(), LaminateService(), CompositionService(), ValidationService())
    result, _ = service.calculate(payload)
    exporter = ExportService(lambda: datetime(2026,10,29,12,30,tzinfo=ZoneInfo("America/Bogota")))
    content = exporter.export(result)
    assert content.startswith(b"\xef\xbb\xbf")
    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    assert len(rows) == 1
    row = rows[0]
    assert row["id_parte_ERP"] == "'000123"
    assert row["material_laminado"][1:] == payload["laminates"][0]["material"]
    assert row["id_registro"][1:] == payload["laminates"][0]["record_id"]
    assert row["id_calculo"] == result.calculation_id
    assert row["fecha_hora_exportacion"] == "2026-10-29T12:30:00-05:00"
    assert row["zona_horaria"] == "America/Bogota"
    assert row["estado_global"] == result.validation.status
    assert D(row["masa_total_mezcla_kg"]) == result.composition.total_mass_kg
    item = result.composition.laminates[0]
    for p in POLYMERS:
        assert D(row[f"masa_{p}_kg"]) == item.masses_kg[p]
        assert D(row[f"fraccion_masica_{p}"]) == item.fractions[p]
        assert D(row[f"espesor_{p}_um"]) == item.thicknesses[p]
        assert D(row[f"densidad_{p}_kg_m3"]) == result.configuration.densities[p]
        assert D(row[f"porcentaje_{p}"]) == result.composition.percentages[p]
        assert D(row[f"masa_total_{p}_kg"]) == result.composition.masses_kg[p]
        criterion = next(c for c in result.validation.criteria if c.polymer == p)
        assert row[f"estado_{p}"] == criterion.status
        assert D(row[f"limite_superior_{p}_porcentaje"]) == criterion.maximum
    assert row["metodologia"] and row["version_aplicacion"]
