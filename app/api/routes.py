from decimal import DecimalException
from flask import Blueprint, current_app, jsonify, request, render_template, Response
from itsdangerous import URLSafeSerializer, BadData
from werkzeug.exceptions import HTTPException
from app.domain.models import DomainError, wire, VERSION, METHOD, LAYERS
from app.domain.parsing import object_fields, number

web = Blueprint("web", __name__)

def services():
    return current_app.extensions["aglurep"]

def signer():
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt="aglurep-calculation-v2")

def body():
    if not request.is_json:
        raise DomainError("Envíe los datos como application/json.", code="invalid_content_type")
    return request.get_json()

@web.before_request
def same_origin():
    if request.method == "POST":
        origin = request.headers.get("Origin")
        if origin and origin != request.host_url.rstrip("/"):
            raise DomainError("La solicitud debe proceder del mismo origen.", code="invalid_origin")

@web.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response

@web.get("/health")
def health():
    return jsonify(status="ok", version=VERSION)

@web.get("/")
def index():
    return render_template("index.html", version=VERSION)

@web.get("/api/configuration")
def configuration():
    return jsonify(configuration=wire(services()["configuration"].defaults()), version=VERSION, methodology=METHOD)

@web.post("/api/laminates")
def create_laminate():
    data = body()
    object_fields(data, ("configuration",), "request")
    config = services()["configuration"].validate(data["configuration"])
    return jsonify(laminate=services()["laminates"].create(config)), 201

@web.post("/api/pe-thickness")
def pe_thickness():
    data = body()
    object_fields(data, ("total_thickness_um", "thicknesses"), "request")
    object_fields(data["thicknesses"], LAYERS, "thicknesses")
    total = number(data["total_thickness_um"], "total_thickness_um", positive=True)
    layers = {p: number(data["thicknesses"][p], "thicknesses." + p) for p in LAYERS}
    value = services()["calculation"].composition.pe_thickness(total, layers)
    return jsonify(pe_thickness_um=wire(value))

@web.post("/api/calculate")
def calculate():
    result, normalized = services()["calculation"].calculate(body())
    snapshot = signer().dumps({"calculation_id": result.calculation_id, "aglurep_id": result.aglurep_id, "methodology": METHOD, "inputs": normalized})
    return jsonify(result=wire(result), snapshot=snapshot)

@web.post("/api/export")
def export():
    data = body()
    object_fields(data, ("snapshot", "inputs"), "request")
    if not isinstance(data["snapshot"], str) or not data["snapshot"]:
        raise DomainError("Recalcule antes de exportar.", field="snapshot", code="invalid_snapshot")
    try:
        snapshot = signer().loads(data["snapshot"])
    except BadData:
        raise DomainError("La instantánea no es válida. Recalcule antes de exportar.", "snapshot", code="invalid_snapshot") from None
    _, _, normalized = services()["calculation"].prepare(data["inputs"])
    if snapshot["methodology"] != METHOD or normalized != snapshot["inputs"]:
        raise DomainError("La mezcla o configuración cambió. Recalcule antes de exportar.", "snapshot", code="stale_snapshot")
    result, _ = services()["calculation"].calculate(normalized, snapshot["calculation_id"], snapshot["aglurep_id"])
    return Response(services()["export"].export(result), content_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{result.aglurep_id}.csv"'})

def register_errors(app):
    @app.errorhandler(DomainError)
    def domain_error(error):
        return jsonify(status="SIN RESULTADOS", errors=[error.to_dict()]), 422

    @app.errorhandler(DecimalException)
    def arithmetic_error(error):
        current_app.logger.exception("Error de aritmética decimal")
        return jsonify(status="SIN RESULTADOS", errors=[{"code": "arithmetic_error", "message": "Los valores exceden la capacidad de cálculo. Revise su magnitud y precisión.", "field": "", "record_id": ""}]), 422

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(status="SIN RESULTADOS", errors=[{"code": f"http_{error.code}", "message": "Solicitud no válida." if error.code == 400 else error.description, "field": "", "record_id": ""}]), error.code

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify(status="SIN RESULTADOS", errors=[{"code": "internal_error", "message": "Ocurrió un error interno. Revise el registro del servidor.", "field": "", "record_id": ""}]), 500
