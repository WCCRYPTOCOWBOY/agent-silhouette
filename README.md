# Silhouette

**Silhouette** is a modular social media automation agent — designed to handle scheduled posting, media prep, and analytics tracking.  
Think of it as the quiet operator in the background, making sure your content hits on time, every time. 🤖✨

---

## 🚀 Features
- **Scheduler loop**: Reads from `post_queue.json`, dispatches posts when due.  
- **Dry-run mode**: Safe testing without firing real posts.  
- **Logging**: Outputs actions and errors to log files.  
- **Queue system**: Each post is tracked with `id`, `text`, `due_at`, and status.  
- **Extensible**: Built to bolt on analytics, retries, and more.  

---

## 📂 Project Structure
