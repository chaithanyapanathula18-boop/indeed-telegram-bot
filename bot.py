import os
import json
import httpx
from datetime import datetime

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SEEN_JOBS_FILE   = "seen_jobs.json"

# ── load / save seen jobs ────────────────────────────────────────
def load_seen():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(ids: set):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(ids), f)

# ── ask Claude to search Indeed ──────────────────────────────────
def search_jobs_via_claude() -> list:
    prompt = """Search Indeed for ALL of these tech jobs in Dublin, Ireland and remote Ireland:
- software engineer
- frontend developer
- backend developer
- fullstack developer
- devops engineer
- cloud engineer
- data engineer
- data scientist
- machine learning engineer
- AI engineer
- mobile developer
- cybersecurity engineer
- QA engineer
- platform engineer

For EVERY job found return a JSON array with this exact format:
[
  {
    "id": "unique job id",
    "title": "job title",
    "company": "company name",
    "location": "location",
    "salary": "salary or null",
    "posted": "date posted",
    "url": "application url",
    "category": "Frontend|Backend|Fullstack|DevOps|Data|AI/ML|Mobile|Security|QA|Other"
  }
]
Return ONLY the JSON array, no other text."""

    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4000,
            "mcp_servers": [
                {
                    "type": "url",
                    "url": "https://mcp.indeed.com/claude/mcp",
                    "name": "indeed-mcp"
                }
            ],
            "messages": [
                {"role": "user", "content": prompt}
            ]
        },
        timeout=60
    )

    data = response.json()
    raw = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            raw += block["text"]

    # parse JSON from response
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())

# ── send Telegram message ────────────────────────────────────────
def send_telegram(text: str):
    httpx.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        },
        timeout=10
    )

# ── main ─────────────────────────────────────────────────────────
def main():
    print(f"[{datetime.now()}] Starting job search...")
    seen = load_seen()

    jobs = search_jobs_via_claude()
    new_jobs = [j for j in jobs if j.get("id") not in seen]

    if not new_jobs:
        print("No new jobs found.")
        return

    # group by category
    grouped = {}
    for job in new_jobs:
        cat = job.get("category", "Other")
        grouped.setdefault(cat, []).append(job)

    # send summary
    lines = "\n".join([f"  {cat}: {len(jobs)}" for cat, jobs in sorted(grouped.items())])
    send_telegram(
        f"🚀 <b>{len(new_jobs)} New Tech Jobs in Ireland!</b>\n"
        f"🕐 {datetime.now().strftime('%d %b %Y, %H:%M')}\n\n{lines}"
    )

    # send each category
    for category, jobs in sorted(grouped.items()):
        emoji = {
            "Frontend": "🎨", "Backend": "⚙️", "Fullstack": "🔄",
            "DevOps": "☁️", "Data": "📊", "AI/ML": "🤖",
            "Mobile": "📱", "Security": "🔒", "QA": "🧪", "Other": "💻"
        }.get(category, "💻")

        send_telegram(f"━━━━━━━━━━━━━━━━\n{emoji} <b>{category}</b> — {len(jobs)} new jobs")

        for job in jobs:
            salary = job.get("salary") or "Not specified"
            send_telegram(
                f"💼 <b>{job['title']}</b>\n"
                f"🏢 {job['company']}\n"
                f"📍 {job['location']}\n"
                f"💰 {salary}\n"
                f"📅 {job.get('posted','')}\n"
                f"🔗 <a href='{job['url']}'>Apply now</a>"
            )
            seen.add(job["id"])

    save_seen(seen)
    print(f"[{datetime.now()}] Done — sent {len(new_jobs)} jobs.")

if __name__ == "__main__":
    main()
    