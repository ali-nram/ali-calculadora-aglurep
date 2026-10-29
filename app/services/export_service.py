"""Un CSV autocontenido; prefijo textual reversible para evitar fórmulas."""
import csv
import io
from datetime import datetime
from zoneinfo import ZoneInfo
from app.domain.models import POLYMERS, LAYERS, VERSION, METHOD, wire, DomainError

class ExportService:
    def __init__(self, clock=None):
        self.clock = clock or (lambda: datetime.now(ZoneInfo("America/Bogota")))

    def export(self, calculation) -> bytes:
        if not calculation.composition.laminates:
            raise DomainError("No hay resultados para exportar.", code="empty_mix")
        result = calculation.composition
        config = calculation.configuration
        timestamp = self.clock().astimezone(ZoneInfo("America/Bogota")).isoformat()
        metadata = {
            "id_calculo": calculation.calculation_id, "fecha_hora_exportacion": timestamp,
            "zona_horaria": "America/Bogota", "version_aplicacion": VERSION, "metodologia": METHOD,
            "perfil_configuracion": calculation.configuration_profile,
            "codificacion_textos": "apostrofo_prefijado_v1: retirar exactamente el primer apostrofo",
            "cantidad_laminados": len(result.laminates), "masa_total_mezcla_kg": result.total_mass_kg,
            "estado_global": calculation.validation.status,
        }
        for p in POLYMERS:
            metadata[f"densidad_{p}_kg_m3"] = config.densities[p]
            metadata[f"objetivo_{p}_porcentaje"] = config.targets[p]
            metadata[f"masa_total_{p}_kg"] = result.masses_kg[p]
            metadata[f"porcentaje_{p}"] = result.percentages[p]
        for p in LAYERS:
            metadata[f"espesor_estandar_{p}_um"] = config.default_thicknesses[p]
        for p, tolerance in config.tolerances.items():
            metadata[f"tolerancia_{p}_puntos_porcentuales"] = tolerance
        for criterion in calculation.validation.criteria:
            p = criterion.polymer
            metadata.update({f"limite_inferior_{p}_porcentaje": criterion.minimum,
                             f"limite_superior_{p}_porcentaje": criterion.maximum,
                             f"diferencia_objetivo_{p}_pp": criterion.difference,
                             f"estado_{p}": criterion.status,
                             f"explicacion_{p}": criterion.explanation})
        rows = []
        for individual in result.laminates:
            source = individual.laminate
            # Todos los textos del usuario se transforman, incluso si ya comienzan con apóstrofo.
            # Esto hace el prefijo inequívoco y reversible, sin interpretar patrones peligrosos.
            row = {**metadata, "id_registro": "'" + source.record_id,
                   "id_parte_ERP": "'" + source.erp_id, "material_laminado": "'" + source.material,
                   "espesor_total_um": source.total_thickness_um, "masa_disponible_kg": source.mass_kg}
            for p in POLYMERS:
                row.update({f"espesor_{p}_um": individual.thicknesses[p],
                            f"contribucion_{p}_um_kg_m3": individual.contributions[p],
                            f"fraccion_masica_{p}": individual.fractions[p],
                            f"masa_{p}_kg": individual.masses_kg[p]})
            rows.append(wire(row))
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        return buffer.getvalue().encode("utf-8-sig")
