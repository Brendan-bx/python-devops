"""Tests for system metrics."""

from api.metrics import get_system_metrics


def test_get_system_metrics_returns_expected_keys():
    """Metrics snapshot must contain CPU, memory and disk percentages."""
    metrics = get_system_metrics()
    assert "cpu_percent" in metrics
    assert "memory_percent" in metrics
    assert "disk_percent" in metrics


def test_get_system_metrics_values_in_range():
    """All percentage values must be between 0 and 100."""
    metrics = get_system_metrics()
    for key in ("cpu_percent", "memory_percent", "disk_percent"):
        assert 0 <= metrics[key] <= 100


def test_get_system_metrics_memory_fields():
    """Memory usage fields must be present and non-negative."""
    metrics = get_system_metrics()
    assert metrics["memory_used_gb"] >= 0
    assert metrics["memory_total_gb"] >= 0
