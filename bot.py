import os
import json
import httpx
from datetime import datetime

TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SEEN_JOBS_FILE    = "/root/seen_jobs.json"

def load_seen():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(ids):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(ids), f)

def search_jobs_via_claude():
    today = datetime.now().strftime("%B %d, %Y")
    prompt = f"""Today is {today}. Use web search to find the latest tech job postings in Dublin, Ireland posted in the last 7 days.

Search for these roles on jobs.ie, irishjobs.ie, linkedin.com/jobs, and indeed.ie:
- Software Engineer Dublin
- Frontend Developer Dublin
- Backend Developer Dublin
- Fullstack Developer Dublin
- DevOps Cloud Engineer Dublin
- Data Engineer Dublin
- AI Machine Learning Engineer Dublin
- Mobile Developer Dublin
- Cybersecurity Engineer Dublin
- QA Engineer Dublin

For every job found return ONLY a raw JSON array (no markdown, no explanation, no code fences):
[
  {{
    "id": "unique_string_based_on_company_and_title",
    "title": "Job Title",
    "company": "Company Name",
    "location": "Dublin, Ireland",
    "salary": "salary range or null",
    "posted": "date posted",
    "url": "direct apply url",
    "category": "Frontend|Backend|Fullstack|DevOps|Data|AI/ML|Mobile|Security|QA|Other"
  }}
]

Return at least 20 jobs. Return ONLY the raw JSON array, nothing else."""

    try:
        res = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 8000,
                "tools": [
                    {
                        "type": "web_search_20250305",
                        "name": "web_search"
                    }
                ],
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=120
        )

        data = res.json()
        print(f"API status: {res.status_code}")

        raw = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                raw += block["text"]

        print(f"Response preview: {raw[:300]}")

        # strip markdown fences if present
        if "```" in raw:
            for part in raw.split("```"):
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("["):
                    raw = part
                    break

        start = raw.find("[")
        end   = raw.rfind("]") + 1
        if start == -1:
            print("No JSON found in response")
            print(f"Full response: {raw[:1000]}")
            return []

        jobs = json.loads(raw[start:end])
        print(f"Parsed {len(jobs)} jobs")
        return jobs

    except Exception as e:
        print(f"Claude API error: {e}")
        return []

def send_telegram(text):
    try:
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
    except Exception as e:
        print(f"Telegram error: {e}")

EMOJI = {
    "Frontend": "🎨", "Backend": "⚙️", "Fullstack": "🔄",
    "DevOps": "☁️",  "Data": "📊",    "AI/ML": "🤖",
    "Mobile": "📱",  "Security": "🔒", "QA": "🧪", "Other": "💻"
}

def main():
    print(f"\n[{datetime.now()}] ── Starting job search ──")
    seen = load_seen()
    jobs = search_jobs_via_claude()

    if not jobs:
        print("No jobs returned.")
        return

    new_jobs = [j for j in jobs if str(j.get("id", "")) not in seen]
    print(f"Total: {len(jobs)} | New: {len(new_jobs)}")

    if not new_jobs:
        print("No new jobs to send.")
        return

    # group by category
    grouped = {}
    for job in new_jobs:
        cat = job.get("category", "Other")
        grouped.setdefault(cat, []).append(job)

    # send summary
    summary = "\n".join([
        f"  {EMOJI.get(c,'💻')} {c}: {len(j)}"
        for c, j in sorted(grouped.items())
    ])
    send_telegram(
        f"🚀 <b>{len(new_jobs)} New Tech Jobs in Ireland!</b>\n"
        f"🕐 {datetime.now().strftime('%d %b %Y, %H:%M')}\n\n{summary}"
    )

    # send each category
    for cat, cat_jobs in sorted(grouped.items()):
        em = EMOJI.get(cat, "💻")
        send_telegram(f"━━━━━━━━━━━━━━━━\n{em} <b>{cat}</b> — {len(cat_jobs)} jobs")
        for job in cat_jobs:
            send_telegram(
                f"💼 <b>{job.get('title','')}</b>\n"
                f"🏢 {job.get('company','')}\n"
                f"📍 {job.get('location', 'Dublin')}\n"
                f"💰 {job.get('salary') or 'Not specified'}\n"
                f"📅 {job.get('posted', '')}\n"
                f"🔗 <a href='{job.get('url','')}'>Apply now</a>"
            )
            seen.add(str(job.get("id", "")))
            print(f"  Sent: {job.get('title')} @ {job.get('company')}")

    save_seen(seen)
    print(f"[{datetime.now()}] Done — sent {len(new_jobs)} jobs.")

if __name__ == "__main__":
    main()
