# Silhouette

Agent Silhouette (Vol. 1 of S.M.A.K.)

Silhouette is the first volume in the S.M.A.K. (Social Media Agent Krew) series.
It’s a modular social media automation agent — designed for scheduled posting, media prep, and analytics tracking.

Think of it as the quiet operator in the pit, making sure your content hits the line on time, every time. 🏁🤖✨

---

🚀 Features

Scheduler loop → Reads from post_queue.json, dispatches posts when due.

Dry-run mode → Safe testing without firing real posts.

Logging → Outputs actions + errors to log files.

Queue system → Each post is tracked with id, text, due_at, and status.

Extensible → Built to bolt on retries, analytics, and more. 

---

## 📂 Project Structure

silhouette/
├─ scheduler.py        # Main loop for dispatching
├─ utils/              # Helpers (metrics, stopwatch, logging)
├─ post_queue.json     # Queue of scheduled posts
├─ logs/               # Log outputs (ignored by git)
└─ README.md

📖 Part of the Series

Vol. 1 — Agent Silhouette → Posting & scheduling.

Vol. 2 — Agent Shroud → Persona-driven chat + voice layer (FastAPI).

Vol. 3 — Agent Loom (future) → Full campaign orchestration, covering the field.
