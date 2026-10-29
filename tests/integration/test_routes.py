from copy import deepcopy
import csv
import io
import pytest

def test_main_routes(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Calculadora de composición" in response.get_data(as_text=True)
    assert b"/static/app.js" in response.data
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200
    data = client.get("/api/configuration").get_json()
    assert data["configuration"]["densities"]["PE"] == "989"
    assert "methodology" in data
    assert "Set-Cookie" not in response.headers
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]

def test_calculation_and_download_match(client, payload):
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["result"]["composition"]["laminates"][0]["thicknesses"]["PE"] == "75"
    exported = client.post("/api/export", json={"snapshot":data["snapshot"],"inputs":payload})
    assert exported.status_code == 200
    assert exported.mimetype == "text/csv"
    assert "attachment;" in exported.headers["Content-Disposition"]
    rows = list(csv.DictReader(io.StringIO(exported.data.decode("utf-8-sig"))))
    assert rows[0]["id_calculo"] == data["result"]["calculation_id"]
    assert rows[0]["estado_global"] == "NO CUMPLE"
    for p in ("PET","PE","PA","EVOH"):
        assert rows[0][f"porcentaje_{p}"] == data["result"]["composition"]["percentages"][p]

@pytest.mark.parametrize("payload", [None, [], {}, {"laminates":[]}, {"configuration":{}, "laminates":[]}])
def test_bad_structure(client, payload):
    response = client.post("/api/calculate", json=payload)
    assert response.status_code in (422,400)
    assert response.get_json()["status"] == "SIN RESULTADOS"

def test_empty_mix(client, payload):
    payload["laminates"] = []
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 422
    assert response.get_json()["errors"][0]["code"] == "empty_mix"

@pytest.mark.parametrize("field,value", [("mass_kg","0"),("mass_kg","-2"),("mass_kg","NaN"),("mass_kg",False),
    ("mass_kg","bad"),("total_thickness_um","10"),("material","")])
def test_server_rejects_bad_fields(client, payload, field, value):
    payload["laminates"][0][field] = value
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 422
    error = response.get_json()["errors"][0]
    assert error["record_id"] == payload["laminates"][0]["record_id"]
    assert error["field"] == field

def test_stale_and_modified_snapshots(client, payload):
    data = client.post("/api/calculate", json=payload).get_json()
    changed = deepcopy(payload); changed["laminates"][0]["mass_kg"] = "21"
    response = client.post("/api/export", json={"snapshot":data["snapshot"],"inputs":changed})
    assert response.status_code == 422
    assert response.get_json()["errors"][0]["code"] == "stale_snapshot"
    changed = deepcopy(payload); changed["configuration"]["densities"]["PET"] = "1399"
    assert client.post("/api/export", json={"snapshot":data["snapshot"],"inputs":changed}).status_code == 422
    assert client.post("/api/export", json={"snapshot":data["snapshot"] + "tampered","inputs":payload}).status_code == 422
    assert client.post("/api/export", json={"snapshot":"","inputs":payload}).status_code == 422

def test_numerically_equivalent_input_matches_snapshot(client, payload):
    data = client.post("/api/calculate", json=payload).get_json()
    payload["laminates"][0]["mass_kg"] = "20.0"
    # Representations with different precision must not accidentally authorize a different snapshot.
    assert client.post("/api/export", json={"snapshot":data["snapshot"],"inputs":payload}).status_code == 422

def test_custom_profile(client, payload):
    payload["configuration"]["densities"]["PE"] = "950"
    data = client.post("/api/calculate", json=payload).get_json()
    assert data["result"]["configuration_profile"] == "Personalizada"
    exported = client.post("/api/export", json={"snapshot":data["snapshot"],"inputs":payload})
    assert "Personalizada" in exported.data.decode("utf-8-sig")

def test_http_errors_and_origin(client, payload):
    assert client.get("/missing").status_code == 404
    assert client.get("/api/calculate").status_code == 405
    assert client.post("/api/calculate", data="{", content_type="application/json").status_code == 400
    assert client.post("/api/calculate", data="a=1").status_code == 422
    response = client.post("/api/calculate", json=payload, headers={"Origin":"https://another.example"})
    assert response.status_code == 422
    assert response.get_json()["errors"][0]["code"] == "invalid_origin"
    assert client.post("/api/calculate", json=payload, headers={"Origin":"http://localhost"}).status_code == 200
    assert client.post("/api/calculate", data=" "*(2*1024*1024+1), content_type="application/json").status_code == 413

@pytest.mark.parametrize("text", ["=1+1", "+1+1", "-1+1", "@SUM(A1)", "'prefijo", "  =1", "0000123", "Ñandú"])
def test_csv_text_protection(client, payload, text):
    payload["laminates"][0]["erp_id"] = text
    data = client.post("/api/calculate", json=payload).get_json()
    response = client.post("/api/export", json={"snapshot":data["snapshot"], "inputs":payload})
    row = next(csv.DictReader(io.StringIO(response.data.decode("utf-8-sig"))))
    assert row["id_parte_ERP"] == "'" + text
    assert row["id_parte_ERP"][1:] == text

def test_dependency_injection_and_controlled_internal_error(app, client, payload):
    class BrokenComposition:
        def calculate(self, rows, config):
            raise RuntimeError("diagnostic test")
    app.extensions["aglurep"]["calculation"].composition = BrokenComposition()
    app.config["TESTING"] = False
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 500
    assert response.get_json()["errors"][0]["code"] == "internal_error"
    assert b"diagnostic test" not in response.data

def test_create_defaults_and_unique_ids(client, payload):
    a = client.post("/api/laminates", json={"configuration":payload["configuration"]})
    b = client.post("/api/laminates", json={"configuration":payload["configuration"]})
    assert a.status_code == 201
    assert a.get_json()["laminate"]["record_id"] != b.get_json()["laminate"]["record_id"]
    assert a.get_json()["laminate"]["thicknesses"] == {"PET":"10","PA":"12","EVOH":"3"}
