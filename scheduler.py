# scheduler.py
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

# --- Project paths ---
QUEUE_PATH = "post_queue.json"
LOG_PATH   = "silhouette_log.txt"

# --- Utilities (your modules) ---
from utils.media_handler import prepare_media           # (media_path: str) -> Any | None
from utils.poster import post_content                   # (text: str, media: Any) -> dict
from utils.metrics import (
    load_metrics, save_metrics, observe_attempt, Stopwatch
)

# ---------------------------
# Logging helpers
# ---------------------------
def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def log_action(msg: str) -> None:
    line = f"[{_utc_now_iso()}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # If logging to file fails, don’t crash the job
        pass

# ---------------------------
# Queue helpers
# ---------------------------
def load_queue() -> List[Dict[str, Any]]:
    """Load posts list from JSON file. Return [] on any error."""
    if not os.path.exists(QUEUE_PATH):
        log_action(f"WARN: queue file not found at {QUEUE_PATH}; starting empty.")
        return []

    try:
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        log_action(f"ERROR loading queue: {e}")
        return []

def maybe_limit(queue: List[Dict[str, Any]], limit: Optional[int]) -> List[Dict[str, Any]]:
    if limit is None or limit <= 0:
        return queue
    return queue[:limit]

# ---------------------------
# Core per-job wrapper (metrics)
# ---------------------------
def process_job_with_metrics(
    job: Dict[str, Any],
    i: int,
    queue_len_after_exec: int,
    *,
    args: argparse.Namespace,
    metrics: Dict[str, Any],
) -> None:
    """
    Wrap one job execution:
      - prepare media
      - post (or dry-run)
      - measure time
      - record success/failure + latency
      - persist metrics atomically
    """
    post_id = str(job.get("id") or job.get("post_id") or f"idx_{i}")

    with Stopwatch() as sw:
        ok = False
        try:
            # Prepare media if present
            media = None
            media_path = job.get("media_path")
            if media_path:
                media = prepare_media(media_path)

            # Execute or dry-run
            text = job.get("text", "")
            if getattr(args, "dry_run", False):
                log_action(f"DRY-RUN: Would post id={post_id!r} text={text!r} media={bool(media_path)}")
            else:
                result = post_content(text, media)
                log_action(f"POSTED: id={post_id} result={result}")

            ok = True

        except Exception as e:
            log_action(f"ERROR posting {post_id}: {e}")
            # Optional: dump stack to the log for debugging
            tb = "".join(traceback.format_exception(*sys.exc_info()))
            log_action(f"TRACE:\n{tb}")
            ok = False

        finally:
            observe_attempt(
                metrics,
                post_id=post_id,
                ok=ok,
                latency_ms=sw.elapsed_ms,
                queue_depth_after=queue_len_after_exec,
            )
            save_metrics(metrics)

# ---------------------------
# CLI / Main
# ---------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Silhouette Scheduler")
    p.add_argument("--dry-run", action="store_true", help="Do everything except actually post")
    p.add_argument("--limit", type=int, default=0, help="Max number of posts to process (0 = all)")
    return p.parse_args()

def main() -> int:
    args = parse_args()

    # Load queue
    queue = load_queue()
    queue = maybe_limit(queue, args.limit)
    if not queue:
        log_action("Queue empty. Nothing to do.")
        # Still stamp metrics so last_run_at updates
        m = load_metrics()
        save_metrics(m)
        return 0

    # Init & stamp metrics
    metrics = load_metrics()
    log_action(f"Starting run: items={len(queue)} dry_run={args.dry_run}")

    # Loop variant: enumerate (preserves list)
    for i, job in enumerate(queue):
        # How many items remain AFTER this attempt:
        queue_len_after = max(0, len(queue) - (i + 1))
        process_job_with_metrics(job, i, queue_len_after, args=args, metrics=metrics)

    # Optional final heartbeat
    save_metrics(metrics)
    log_action("Run complete.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
