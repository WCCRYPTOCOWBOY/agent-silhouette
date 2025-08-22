# utils/metrics.py
from __future__ import annotations

import json, os, time, tempfile
from datetime import datetime
from typing import Dict, Any

METRICS_PATH = "metrics.json"

DEFAULTS: Dict[str, Any] = {
    "first_run_at": None,     # ISO timestamp (UTC)
    "last_run_at":  None,     # ISO timestamp (UTC)
    "total_processed": 0,     # all attempts (success + error)
    "success_count":  0,      # ok == True
    "error_count":    0,      # ok == False
    "avg_latency_ms": 0.0,    # online moving average
    "last_post_id":   None,   # last processed job id
    "queue_depth":    0,      # # of not-yet-posted items after last run
}

def _utc_now_iso() -> str:
    # Trim microseconds and append Z to be explicit UTC
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_metrics() -> Dict[str, Any]:
    """Load metrics from disk, merging with DEFAULTS to keep forward compatibility."""
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH, "r", encoding="utf-8") as f:
                m = json.load(f)
        except Exception:
            m = DEFAULTS.copy()
    else:
        m = DEFAULTS.copy()

    # Ensure all keys exist even if the file is from an older version
    merged = {**DEFAULTS, **m}
    if merged["first_run_at"] is None:
        merged["first_run_at"] = _utc_now_iso()
    return merged

def save_metrics(m: Dict[str, Any]) -> None:
    """Persist metrics to disk atomically to avoid partial writes."""
    m["last_run_at"] = _utc_now_iso()
    # Write to a temp file and then replace
    dirpath = os.path.dirname(os.path.abspath(METRICS_PATH)) or "."
    fd, tmp = tempfile.mkstemp(prefix="metrics_", suffix=".json", dir=dirpath)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)
        os.replace(tmp, METRICS_PATH)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def observe_attempt(
    metrics: Dict[str, Any], *,
    post_id: str,
    ok: bool,
    latency_ms: float,
    queue_depth_after: int
) -> Dict[str, Any]:
    """
    Update counters after a job attempt using an online mean for latency.
    """
    tp = int(metrics.get("total_processed", 0)) + 1
    prev_avg = float(metrics.get("avg_latency_ms", 0.0))
    new_avg = prev_avg + (latency_ms - prev_avg) / tp

    metrics["total_processed"] = tp
    metrics["avg_latency_ms"] = round(new_avg, 4)
    metrics["success_count"] = int(metrics.get("success_count", 0)) + (1 if ok else 0)
    metrics["error_count"]   = int(metrics.get("error_count", 0)) + (0 if ok else 1)
    metrics["last_post_id"]  = post_id
    metrics["queue_depth"]   = int(queue_depth_after)
    return metrics

class Stopwatch:
    """
    Usage:
        with Stopwatch() as sw:
            ... do work ...
        print(sw.ms)       # milliseconds
        print(sw.seconds)  # seconds
    """
    def __enter__(self):
        self._t0 = time.perf_counter()
        self.ms = 0.0
        return self

    def __exit__(self, *exc):
        self.ms = (time.perf_counter() - self._t0) * 1000.0

    @property
    def seconds(self) -> float:
        return self.ms / 1000.0

    # Nice alias if your scheduler is using 'elapsed_ms'
    @property
    def elapsed_ms(self) -> float:
        return self.ms
