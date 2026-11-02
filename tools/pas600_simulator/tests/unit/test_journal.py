"""Local evidence state rejects overwrite and survives interrupted replacement."""
import json
from unittest.mock import patch
import pytest
from pas600_simulator.journal import LocalRun, atomic_json


def test_new_run_and_interruption(tmp_path):
    """Failed rename preserves prior durable state; nonempty output cannot be reused."""
    run = LocalRun.create(tmp_path / 'run', 'abc')
    state = tmp_path / 'run/control/run.json'
    assert json.loads(state.read_text())['state'] == 'generating'
    with patch('pas600_simulator.journal.os.replace', side_effect=OSError('interrupted')):
        with pytest.raises(OSError):
            atomic_json(state, {'state': 'generated'})
    assert json.loads(state.read_text())['state'] == 'generating'
    assert str(run.id)
    with pytest.raises(ValueError):
        LocalRun.create(tmp_path / 'run', 'abc')
