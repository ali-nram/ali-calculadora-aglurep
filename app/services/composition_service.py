from decimal import Decimal, localcontext
from app.domain.models import POLYMERS, LAYERS, Composition, LaminateResult, DomainError

class CompositionService:
    def calculate(self, laminates, configuration) -> Composition:
        if not laminates:
            raise DomainError("Agregue al menos un laminado para calcular.", code="empty_mix")
        with localcontext() as ctx:
            ctx.prec = 50
            results = []
            for row in laminates:
                thicknesses = dict(row.thicknesses)
                pe = row.total_thickness_um - sum(thicknesses.values(), Decimal(0))
                if pe < 0:
                    raise DomainError("Las capas PET, PA y EVOH superan el espesor total.", "total_thickness_um", row.record_id)
                thicknesses["PE"] = pe
                contributions = {p: thicknesses[p] * configuration.densities[p] for p in POLYMERS}
                total = sum(contributions.values(), Decimal(0))
                if not total.is_finite() or total <= 0:
                    raise DomainError("La suma de contribuciones debe ser positiva.", "thicknesses", row.record_id)
                fractions = {p: contributions[p] / total for p in POLYMERS}
                masses = {p: row.mass_kg * fractions[p] for p in POLYMERS}
                self._consistent(sum(masses.values()), row.mass_kg)
                results.append(LaminateResult(row, thicknesses, contributions, fractions, masses))
            total_mass = sum((r.laminate.mass_kg for r in results), Decimal(0))
            masses = {p: sum((r.masses_kg[p] for r in results), Decimal(0)) for p in POLYMERS}
            percentages = {p: 100 * masses[p] / total_mass for p in POLYMERS}
            self._consistent(sum(masses.values()), total_mass)
            self._consistent(sum(percentages.values()), Decimal(100))
            return Composition(tuple(results), total_mass, masses, percentages)

    @staticmethod
    def _consistent(actual, expected):
        if abs(actual - expected) > abs(expected) * Decimal("1e-12"):
            raise DomainError("El cálculo no conserva masa o porcentajes.", code="inconsistent_result")
