from copy import deepcopy
from decimal import Decimal as D, localcontext
import pytest
from app.services.laminate_service import LaminateService
from app.services.composition_service import CompositionService

def calculate(rows, config):
    return CompositionService().calculate(LaminateService().selected(rows), config)

def test_independent_formula(row, config):
    result = calculate([row], config)
    item = result.laminates[0]
    assert item.thicknesses["PE"] == D("75")
    assert item.contributions == {"PET": D("14000"), "PE": D("74175"), "PA": D("11796"), "EVOH": D("2841")}
    with localcontext() as ctx:
        ctx.prec = 50
        assert item.fractions["PET"] == D("14000") / D("102812")
        assert item.masses_kg["PET"] == D("20") * (D("14000") / D("102812"))
    assert abs(sum(item.masses_kg.values()) - D("20")) < D("1e-25")
    assert abs(sum(result.percentages.values()) - 100) < D("1e-25")

@pytest.mark.parametrize("polymer", ["PET", "PE", "PA", "EVOH"])
def test_single_polymer(row, config, polymer):
    row["thicknesses"] = {p: "100" if p == polymer else "0" for p in ("PET", "PA", "EVOH")}
    result = calculate([row], config)
    assert result.masses_kg[polymer] == D("20")
    assert result.percentages[polymer] == 100
    for p in result.masses_kg:
        if p != polymer:
            assert result.masses_kg[p] == 0

def test_zero_layer_and_multiple_rows(row, config):
    row["thicknesses"]["PA"] = "0"
    second = deepcopy(row)
    second.update(record_id="00000000-0000-4000-8000-000000000002", mass_kg="7.25", total_thickness_um="200.125")
    result = calculate([row, second], config)
    assert result.total_mass_kg == D("27.25")
    assert result.masses_kg["PA"] == 0
    for p in result.masses_kg:
        with localcontext() as ctx:
            ctx.prec = 50
            assert result.masses_kg[p] == sum(x.masses_kg[p] for x in result.laminates)
    assert abs(sum(result.percentages.values()) - 100) < D("1e-25")

def test_no_intermediate_rounding(row, config):
    row.update(mass_kg="0.1234567890123456789012345678", total_thickness_um="100.1234567890123456789012345")
    result = calculate([row], config)
    with localcontext() as ctx:
        ctx.prec = 50
        pe = D(row["total_thickness_um"]) - 25
        denominator = D("14000") + D("11796") + D("2841") + pe * D("989")
        assert result.laminates[0].masses_kg["PET"] == D(row["mass_kg"]) * (D("14000") / denominator)
    assert len(result.laminates[0].fractions["PET"].as_tuple().digits) > 28
