"""Load synthetic scenarios without accepting or persisting measurements."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def scenarios():
    """Return independent JSON inputs/expectations; all IDs and the zone are synthetic."""
    return json.loads((Path(__file__).parents[2] / "fixtures/consumption/scenarios.json").read_text())
