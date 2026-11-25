"""External dashboard rendering applies the same explicit007 policy to platform and008 views."""

import json

from scripts.observability.render_dashboard import render


def test_both_known_dashboards_receive_the_selected_policy(tmp_path):
    """The008 panel must not disappear when deployment uses an external generated dashboard directory."""
    output = tmp_path / "dashboards"
    result = render("test", "test-sampling-v2", 0.1, output)
    assert result == output / "platform.json"
    for name in ["platform.json", "notifications.json"]:
        path = output / name
        dashboard = json.loads(path.read_text())
        panel = next(
            panel
            for panel in dashboard["panels"]
            if panel["type"] == "ecsec-coverage-panel"
        )
        assert panel["options"] == {"revision": "test-sampling-v2", "traceRatio": 0.1}
        assert (
            next(
                v for v in dashboard["templating"]["list"] if v["name"] == "environment"
            )["current"]["value"]
            == "test"
        )
        assert path.stat().st_mode & 0o777 == 0o600
