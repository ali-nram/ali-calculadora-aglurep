from flask import Flask
from .config import settings
from .services.configuration_service import ConfigurationService
from .services.laminate_service import LaminateService
from .services.composition_service import CompositionService
from .services.validation_service import ValidationService
from .services.export_service import ExportService
from .services.calculation_service import CalculationService

def create_app(test_config=None, *, services=None):
    app = Flask(__name__)
    app.config.update(settings())
    if test_config:
        app.config.update(test_config)
    if app.config["BEHIND_PROXY"]:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=0, x_proto=1, x_host=0, x_port=0, x_prefix=0)
    supplied = services or {}
    configuration = supplied.get("configuration", ConfigurationService())
    laminates = supplied.get("laminates", LaminateService())
    composition = supplied.get("composition", CompositionService())
    validation = supplied.get("validation", ValidationService())
    app.extensions["aglurep"] = {
        "configuration": configuration, "laminates": laminates,
        "calculation": CalculationService(configuration, laminates, composition, validation),
        "export": supplied.get("export", ExportService()),
    }
    from .api.routes import web, register_errors
    app.register_blueprint(web)
    register_errors(app)
    return app
