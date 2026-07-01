"""System metrics collection via psutil."""

import psutil


def get_system_metrics() -> dict:
    """
    Return a non-blocking snapshot of CPU, memory and disk usage.

    Uses ``interval=None`` for cpu_percent so the call never blocks the
    event loop.
    """
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": memory.percent,
        "disk_percent": disk.percent,
        "memory_used_gb": round(memory.used / 1e9, 2),
        "memory_total_gb": round(memory.total / 1e9, 2),
    }
