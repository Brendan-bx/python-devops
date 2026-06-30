"""System metrics helper using psutil."""

import psutil


def get_system_metrics() -> dict:
    """
    Return a snapshot of the current machine's CPU, memory and disk usage.

    Uses ``psutil.cpu_percent(interval=None)`` (non-blocking).
    """
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": mem.percent,
        "memory_used_gb": round(mem.used / (1024**3), 2),
        "memory_total_gb": round(mem.total / (1024**3), 2),
        "disk_percent": disk.percent,
    }
