"""Flujo HTTP determinista; complementa la verificación manual del DOM."""
from copy import deepcopy
from decimal import Decimal as D
import csv
import json
import io

def test_add_edit_remove_recalculate_export_reset(client, config):
    from app.domain.models import wire
    from app.services.laminate_service import LaminateService
    configuration = wire(config)
    rows = []
    for material,mass in (("PET/HBA","20"),("PET/Flexible","5.5")):
        row = client.post("/api/laminates", json={"configuration":configuration}).get_json()["laminate"]
        row.update(erp_id="000123" if not rows else "000124",material=material,total_thickness_um="100",mass_kg=mass)
        rows.append(row)
    payload = {"configuration":configuration,"laminates":deepcopy(rows)}
    first = client.post("/api/calculate", json=payload).get_json()
    assert first["result"]["composition"]["total_mass_kg"] == "25.5"
    rows[1]["mass_kg"] = "7"
    rows[1]["thicknesses"]["PA"] = "0"
    payload["laminates"] = deepcopy(rows)
    edited = client.post("/api/calculate", json=payload).get_json()
    assert edited["result"]["composition"]["total_mass_kg"] == "27"
    assert edited["result"]["composition"]["laminates"][1]["laminate"]["thicknesses"]["PA"] == "0"
    assert client.post("/api/export", json={"snapshot":first["snapshot"],"inputs":payload}).status_code == 422
    rows.pop(0)
    payload["laminates"] = deepcopy(rows)
    current = client.post("/api/calculate", json=payload).get_json()
    exported = client.post("/api/export", json={"snapshot":current["snapshot"],"inputs":payload})
    records = list(csv.DictReader(io.StringIO(exported.data.decode("utf-8-sig"))))
    assert len(records) == 1
    assert json.loads(records[0]["partes_laminados_ERP"]) == ["000124"]
    assert records[0]["cantidad_laminados"] == "1"
    assert {r["id_aglurep"] for r in records} == {current["result"]["aglurep_id"]}
    assert abs(sum(D(records[0][f"masa_{p}_kg"]) for p in ("PET","PE","PA","EVOH")) - D("7")) <= D("0.02")
    assert records[0]["masa_PA_kg"] == "0.00"
    payload["laminates"] = []
    assert client.post("/api/calculate", json=payload).get_json()["status"] == "SIN RESULTADOS"
    assert client.post("/api/export", json={"snapshot":current["snapshot"],"inputs":payload}).status_code == 422

def test_two_active_rows_one_calculation_id(client, payload):
    second = deepcopy(payload["laminates"][0])
    second["record_id"] = "00000000-0000-4000-8000-000000000002"
    payload["laminates"].append(second)
    current = client.post("/api/calculate", json=payload).get_json()
    exported = client.post("/api/export", json={"snapshot":current["snapshot"],"inputs":payload})
    records = list(csv.DictReader(io.StringIO(exported.data.decode("utf-8-sig"))))
    assert len(records) == 1
    assert records[0]["cantidad_laminados"] == "2"
    assert json.loads(records[0]["partes_laminados_ERP"]) == ["000123", "000123"]
    assert {r["id_aglurep"] for r in records} == {current["result"]["aglurep_id"]}

def test_real_mixture_at_exact_pet_limit(client, payload):
    payload["laminates"] = []
    for index, (polymer,mass) in enumerate((("PET","10"),("PE","83"),("PA","4"),("EVOH","3")), 1):
        payload["laminates"].append({"record_id":f"00000000-0000-4000-8000-{index:012d}", "erp_id":"000123", "material":polymer,
            "mass_kg":mass,"total_thickness_um":"100", "thicknesses":{p:"100" if p == polymer else "0" for p in ("PET","PA","EVOH")}})
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 200
    result = response.get_json()["result"]
    assert result["composition"]["percentages"]["PET"] == "10"
    assert result["validation"]["status"] == "CUMPLE"
