from decimal import Decimal, localcontext
from app.domain.models import POLYMERS, Criterion, Validation

class ValidationService:
    def validate(self, composition, configuration) -> Validation:
        if composition is None or not composition.laminates:
            return Validation("SIN RESULTADOS", ())
        criteria = []
        with localcontext() as ctx:
            ctx.prec = 50
            for p in POLYMERS:
                value, target = composition.percentages[p], configuration.targets[p]
                low = Decimal(0) if p == "PET" else max(Decimal(0), target - configuration.tolerances[p])
                high = configuration.pet_limit if p == "PET" else min(Decimal(100), target + configuration.tolerances[p])
                passes = low <= value <= high
                explanation = "Dentro del intervalo permitido."
                if value < low:
                    explanation = f"El contenido de {p} está por debajo del mínimo permitido."
                elif value > high:
                    explanation = f"El contenido de {p} supera el máximo permitido."
                criteria.append(Criterion(p, value, target, low, high, value - target,
                                           "CUMPLE" if passes else "NO CUMPLE", explanation))
        return Validation("CUMPLE" if all(c.status == "CUMPLE" for c in criteria) else "NO CUMPLE", tuple(criteria))
