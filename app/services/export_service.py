"""CSV resumen: una fila por Aglurep y lista ERP reversible en JSON."""
import csv
import io
import json
from decimal import Decimal, ROUND_HALF_UP, localcontext
from app.domain.models import POLYMERS, wire, DomainError

def csv_decimal(value):
    """Redondeo de salida; nunca modifica el resultado del dominio."""
    with localcontext() as context:
        context.prec = 50
        return format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f")

class ExportService:
    def export(self, calculation) -> bytes:
        composition = calculation.composition
        if not composition.laminates:
            raise DomainError("No hay resultados para exportar.", code="empty_mix")
        row = {
            "id_aglurep": calculation.aglurep_id,
            "cantidad_laminados": len(composition.laminates),
            # El prefijo fijo [ de JSON evita interpretar el contenido como formula.
            # Las partes son strings: conserva ceros, duplicados y delimitadores originales.
            "partes_laminados_ERP": json.dumps(
                [item.laminate.erp_id for item in composition.laminates], ensure_ascii=False),
            "estado_global": calculation.validation.status,
        }
        row.update({f"masa_{p}_kg": csv_decimal(composition.masses_kg[p]) for p in POLYMERS})
        row.update({f"porcentaje_{p}": csv_decimal(composition.percentages[p]) for p in POLYMERS})
        row["perfil_configuracion"] = calculation.configuration_profile
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(wire(row))
        return buffer.getvalue().encode("utf-8-sig")
