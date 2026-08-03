"""
IndoLens - Performance Measurement Module
Measures computation metrics (Time, FPS, CPU, Memory, Frames) during evaluation.
"""

import time
import psutil
from typing import Dict, Any

def measure_processing_time(start_time: float, end_time: float) -> float:
    """Calculate elapsed processing time in seconds."""
    return round(end_time - start_time, 4)

def measure_fps(total_frames: int, elapsed_time: float) -> float:
    """Calculate Frames Per Second (FPS)."""
    if elapsed_time <= 0:
        return 0.0
    return round(total_frames / elapsed_time, 2)

def measure_memory() -> Dict[str, float]:
    """Measure current process memory usage in MB and percentage."""
    process = psutil.Process()
    mem_info = process.memory_info()
    return {
        "rss_mb": round(mem_info.rss / (1024 * 1024), 2),
        "vsz_mb": round(mem_info.vms / (1024 * 1024), 2),
        "percent": round(process.memory_percent(), 2)
    }

def measure_cpu() -> float:
    """Measure current CPU utilization percentage."""
    return round(psutil.cpu_percent(interval=0.1), 2)

def measure_processed_frames(total_frames: int) -> int:
    """Record total frames evaluated."""
    return total_frames

def get_performance_summary(start_time: float, end_time: float, total_frames: int) -> Dict[str, Any]:
    """Get complete performance metrics dictionary."""
    elapsed = measure_processing_time(start_time, end_time)
    fps = measure_fps(total_frames, elapsed)
    mem = measure_memory()
    cpu = measure_cpu()
    frames = measure_processed_frames(total_frames)

    return {
        "processing_time_sec": elapsed,
        "fps": fps,
        "total_frames_processed": frames,
        "memory_mb": mem["rss_mb"],
        "memory_percent": mem["percent"],
        "cpu_percent": cpu
    }
