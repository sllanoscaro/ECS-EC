"""Local CSV contract checks; original revision19 documentary review remains deferred."""
import csv
import io
from datetime import datetime, UTC
from decimal import Decimal
from pas600_simulator.csv_writer import encode_csv
from pas600_simulator.scenario import SimulationScenario


def test_known_csv():
    """Quoted UTF8/CRLF preserves native columns, exact 100/104 and publisher identity."""
    scenario = SimulationScenario()
    meter = scenario.categories[2].meter.model_copy(update={'device_name': 'Medidor "energía", exterior'})
    data = encode_csv(scenario, meter, [(datetime(2026, 1, 1, tzinfo=UTC), Decimal(100)), (datetime(2026, 1, 1, 0, 15, tzinfo=UTC), Decimal(104))])
    rows = list(csv.reader(io.StringIO(data.decode('utf-8'))))
    assert len(rows) == 9 and rows[1][-1] == '2'
    assert rows[1][1] == 'SYNTHETIC-PAS600'
    assert rows[1][4] == 'Medidor "energía", exterior'
    assert rows[3][:3] == ['', '', ''] and rows[4][3] == meter.csv_topic_id
    assert rows[7] == ['0', '0', '2026-01-01 00:00:00', '100']
    assert rows[8] == ['0', '0', '2026-01-01 00:15:00', '104']
    assert data.count(b'\r\n') == 9
