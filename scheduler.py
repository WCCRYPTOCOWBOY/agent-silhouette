# scheduler.py — Silhouette

import os, json, time
from datetime import datetime
from utils.poster import post_content
from utils.media_handler import prepare_media

def getenv_any(names: list[str], default: str | None = None) -> str | None:
    for n in names:
        v = os.getenv(n)
        if v is not None:
            return v
    return default

AGENT_NAME = getenv_any(["SILHOUETTE_NAME"], "Silhouette")

QUEUE_FILE = getenv_any(
    ["SILHOUETTE_QUEUE_FILE", "SHROUD_QUEUE_FILE"],
    "post_queue.json"
)
LOG_FILE = getenv_any(
    ["SILHOUETTE_LOG_FILE", "SHROUD_LOG_FILE"],
    "silhouette_log.txt"
)
SLEEP_SEC = int(getenv_any(
    ["SILHOUETTE_DISPATCH_INTERVAL_SECONDS", "SHROUD_DISPATCH_INTERVAL_SECONDS"],
    "15"
))
DRY_RUN = (getenv_any(
    ["SILHOUETTE_DRY_RUN", "SHROUD_DRY_RUN"],
    "true"
) or "true").lower() == "true"

def log_action(msg: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} - {msg}\n")

def load_queue():
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_queue(q):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(q, f, indent=2, ensure_ascii=False)

def parse_due(post):
    """Accept 'timestamp' (YYYY-MM-DD HH:MM or ISO) OR epoch 'scheduled_ts'."""
    if "scheduled_ts" in post and isinstance(post["scheduled_ts"], (int, float)):
        return datetime.fromtimestamp(int(post["scheduled_ts"]))
    ts = post.get("timestamp")
    if not ts:
        return None  # treat as 'now'
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None  # if unparseable, run now

def is_due(post, now_dt):
    due = parse_due(post)
    return (due is None) or (due <= now_dt)

def main_loop():
    log_action(f"{AGENT_NAME} scheduler started.")
    while True:
        now_dt = datetime.now()
        queue = load_queue()
        updated = False

        for post in queue:
            if post.get("posted"):
                continue
            if not is_due(post, now_dt):
                continue

            text = post.get("text", "")
            media_path = post.get("media_path", "")

            try:
                log_action(f"Dispatching: {post.get('id', text[:32])} (dry_run={DRY_RUN})")
                media = prepare_media(media_path) if media_path else None
                if DRY_RUN:
                    log_action(f"[DRY RUN] Would post: '{text}' media={media}")
                    result = {"ok": True, "mock": True}
                else:
                    result = post_content(text, media)
                    log_action(f"Post result: {result}")
                post["posted"] = True
                post["posted_at"] = now_dt.isoformat()
                post["result"] = result
                updated = True
            except Exception as e:
                log_action(f"ERROR dispatching '{text[:32]}': {e}")

        if updated:
            save_queue(queue)

        time.sleep(SLEEP_SEC)

if __name__ == "__main__":
    main_loop()
