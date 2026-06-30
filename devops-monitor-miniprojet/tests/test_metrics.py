"""Unit tests for get_system_metrics()."""

from api.metrics import get_system_metrics


def test_metrics_keys() -> None:
    metrics = get_system_metrics()
    assert "cpu_percent" in metrics
    assert "memory_percent" in metrics
    assert "disk_percent" in metrics


def test_metrics_values_in_range() -> None:
    metrics = get_system_metrics()
    for key in ("cpu_percent", "memory_percent", "disk_percent"):
        assert 0 <= metrics[key] <= 100
