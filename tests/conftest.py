from copy import deepcopy
from uuid import UUID
import pytest
from app import create_app
from app.domain.models import wire
from app.services.configuration_service import ConfigurationService

@pytest.fixture
def config():
    return ConfigurationService().defaults()

@pytest.fixture
def row():
    return {"record_id": "00000000-0000-4000-8000-000000000001", "erp_id": "000123",
            "material": "PET/HBA flexible español", "total_thickness_um": "100", "mass_kg": "20",
            "thicknesses": {"PET": "10", "PA": "12", "EVOH": "3"}}

@pytest.fixture
def payload(config, row):
    return {"configuration": wire(config), "laminates": [deepcopy(row)]}

@pytest.fixture
def app():
    return create_app({"TESTING": True, "SECRET_KEY": "deterministic-test-secret"})

@pytest.fixture
def client(app):
    return app.test_client()
