from decimal import Decimal, localcontext
from uuid import UUID, uuid4
from app.domain.models import Laminate, LAYERS, DomainError
from app.domain.parsing import object_fields, number, text

class LaminateService:
    def create(self, configuration) -> dict:
        return {"record_id": str(uuid4()), "erp_id": "", "material": "", "mass_kg": "",
                "total_thickness_um": "", "thicknesses": {p: str(configuration.default_thicknesses[p]) for p in LAYERS}}

    def validate(self, data) -> Laminate:
        object_fields(data, ("record_id", "erp_id", "material", "total_thickness_um", "mass_kg", "thicknesses"), "laminates")
        record_id = data["record_id"]
        try:
            if not isinstance(record_id, str) or str(UUID(record_id)) != record_id:
                raise ValueError
        except ValueError:
            raise DomainError("ID de registro UUID no válido.", "record_id") from None
        object_fields(data["thicknesses"], LAYERS, "thicknesses", record_id)
        layers = {p: number(data["thicknesses"][p], f"thicknesses.{p}", record_id) for p in LAYERS}
        total = number(data["total_thickness_um"], "total_thickness_um", record_id, positive=True)
        with localcontext() as ctx:
            ctx.prec = 50
            if sum(layers.values(), Decimal(0)) > total:
                raise DomainError("Las capas PET, PA y EVOH superan el espesor total.", "total_thickness_um", record_id)
        return Laminate(record_id, text(data["erp_id"], "erp_id", record_id),
                        text(data["material"], "material", record_id), total,
                        number(data["mass_kg"], "mass_kg", record_id, positive=True), layers)

    def selected(self, data) -> tuple[Laminate, ...]:
        if not isinstance(data, list) or len(data) > 500:
            raise DomainError("Envíe una lista de hasta 500 laminados.", "laminates")
        rows = tuple(self.validate(row) for row in data)
        if len({r.record_id for r in rows}) != len(rows):
            raise DomainError("Los ID de registro deben ser únicos.", "record_id")
        return rows

    def edit(self, rows, record_id, changes):
        from app.domain.models import wire
        if "record_id" in changes:
            raise DomainError("El ID de registro no se puede modificar.", "record_id", record_id)
        result, found = [], False
        for row in rows:
            if row.record_id == record_id:
                row = self.validate({**wire(row), **changes})
                found = True
            result.append(row)
        if not found:
            raise DomainError("Registro no encontrado.", "record_id", record_id)
        return tuple(result)

    def remove(self, rows, record_id):
        if not any(row.record_id == record_id for row in rows):
            raise DomainError("Registro no encontrado.", "record_id", record_id)
        return tuple(row for row in rows if row.record_id != record_id)
