from uuid import uuid4
from app.domain.models import Calculation, DomainError, wire
from app.domain.parsing import object_fields
from app.domain.contracts import ConfigurationPort, LaminatePort, CompositionPort, ValidationPort

class CalculationService:
    def __init__(self, configuration: ConfigurationPort, laminates: LaminatePort,
                 composition: CompositionPort, validation: ValidationPort):
        self.configuration, self.laminates = configuration, laminates
        self.composition, self.validation = composition, validation

    def prepare(self, data):
        object_fields(data, ("configuration", "laminates"), "request")
        config = self.configuration.validate(data["configuration"])
        rows = self.laminates.selected(data["laminates"])
        normalized = {"configuration": wire(config), "laminates": wire(rows)}
        return config, rows, normalized

    def calculate(self, data, calculation_id=None, aglurep_id=None):
        config, rows, normalized = self.prepare(data)
        composition = self.composition.calculate(rows, config)
        result = Calculation(calculation_id or str(uuid4()), config, self.configuration.profile(config),
                             composition, self.validation.validate(composition, config), aglurep_id or "AGL-" + str(uuid4()))
        return result, normalized
