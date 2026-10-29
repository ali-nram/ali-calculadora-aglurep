from decimal import Decimal as D, localcontext
from app.domain.models import TechnicalConfiguration, POLYMERS, LAYERS, DomainError
from app.domain.parsing import object_fields, number

class ConfigurationService:
    def defaults(self) -> TechnicalConfiguration:
        return TechnicalConfiguration(
            dict(zip(POLYMERS, map(D, ("1400", "989", "983", "947")))),
            dict(zip(LAYERS, map(D, ("10", "12", "3")))),
            dict(zip(POLYMERS, map(D, ("9.5", "83.5", "4", "3")))),
            {p: D("5") for p in ("PE", "PA", "EVOH")}, D("10"))

    def validate(self, data) -> TechnicalConfiguration:
        object_fields(data, ("densities", "default_thicknesses", "targets", "tolerances", "pet_limit"), "configuration")
        parsed = {}
        for group, keys in (("densities", POLYMERS), ("default_thicknesses", LAYERS),
                            ("targets", POLYMERS), ("tolerances", ("PE", "PA", "EVOH"))):
            object_fields(data[group], keys, "configuration." + group)
            parsed[group] = {p: number(data[group][p], f"configuration.{group}.{p}", positive=group == "densities") for p in keys}
        limit = number(data["pet_limit"], "configuration.pet_limit")
        for group in ("targets", "tolerances"):
            if any(v > 100 for v in parsed[group].values()):
                raise DomainError("Los porcentajes deben estar entre 0 y 100.", "configuration." + group)
        with localcontext() as ctx:
            ctx.prec = 50
            if sum(parsed["targets"].values()) != D("100"):
                raise DomainError("Los objetivos deben sumar 100 %.", "configuration.targets")
        if limit > 100 or parsed["targets"]["PET"] > limit:
            raise DomainError("El límite PET debe estar entre su objetivo y 100 %.", "configuration.pet_limit")
        return TechnicalConfiguration(**parsed, pet_limit=limit)

    def profile(self, config: TechnicalConfiguration) -> str:
        return "Aglurep v1" if config == self.defaults() else "Personalizada"
