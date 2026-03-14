import os
import json
import httpx
from datetime import datetime

TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SEEN_JOBS_FILE    = "seen_jobs.json"

def load_seen():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(ids):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(ids), f)

SEARCHES = [
    "software engineer jobs Dublin Ireland indeed.ie 2026",
    "frontend developer jobs Dublin Ireland indeed.ie 2026",
    "backend developer jobs Dublin Ireland indeed.ie 2026",
    "fullstack developer jobs Dublin Ireland indeed.ie 2026",
    "devops cloud engineer jobs Dublin Ireland indeed.ie 2026",
    "data engineer scientist jobs Dublin Ireland indeed.ie 2026",
    "machine learning AI engineer jobs Dublin Ireland indeed.ie 2026",
    "mobile iOS Android developer jobs Dublin Ireland indeed.ie 2026",
    "cybersecurity engineer jobs Dublin Ireland indeed.ie 2026",
    "QA automation engineer jobs Dublin Ireland indeed.ie 2026",
]

def search_jobs(query: str) -> list:
    today = datetime.now().strftime("%B %d, %Y")
    prompt = f"""Today is {today}.

Search the web for: "{query}"

From ALL the search results, extract every individual job posting you can find.
Look carefully at results from indeed.ie, irishjobs.ie, jobs.ie, linkedin.com.

For each job posting return it in this JSON format.
Return ONLY a raw JSON array, nothing else, no markdown, no explanation:
[
  {{
    "id": "companyname-jobtitle-uniqueid",
    "title": "exact job title",
    "company": "company name",
    "location": "Dublin, Ireland",
    "salary": "salary if shown else null",
    "posted": "date posted if shown else null",
    "url": "full direct URL to the job posting",
    "category": "Frontend|Backend|Fullstack|DevOps|Data|AI/ML|Mobile|Security|QA|Other"
  }}
]

If no jobs found return: []
Return ONLY the raw JSON array. No text before or after."""

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
                "max_tokens": 4000,
                "tools": [{"type": "web_search_20250305", "name": "web_search"}],
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=60
        )

        data = res.json()
        raw  = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                raw += block["text"]

        if not raw.strip():
            return []

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
            return []

        jobs = json.loads(raw[start:end])
        return [j for j in jobs if j.get("url") and j.get("title")]

    except Exception as e:
        print(f"  Error [{query[:50]}]: {e}")
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
    "Frontend":  "🎨", "Backend":   "⚙️", "Fullstack": "🔄",
    "DevOps":    "☁️", "Data":      "📊", "AI/ML":     "🤖",
    "Mobile":    "📱", "Security":  "🔒", "QA":        "🧪",
    "Other":     "💻"
}

def main():
    print(f"\n[{datetime.now()}] ── Starting job search ──")

    # send hi message every run
    send_telegram(
        f"👋 <b>Hi! Job search starting...</b>\n"
        f"🕐 {datetime.now().strftime('%d %b %Y, %H:%M')}"
    )

    seen     = load_seen()
    all_jobs = []

    for i, query in enumerate(SEARCHES, 1):
        print(f"  [{i}/{len(SEARCHES)}] {query[:65]}...")
        jobs = search_jobs(query)
        print(f"  Found: {len(jobs)}")
        all_jobs.extend(jobs)

    # deduplicate within this run
    seen_this_run = set()
    unique_jobs   = []
    for job in all_jobs:
        jid = str(job.get("id", "")).lower().strip()
        if jid and jid not in seen_this_run:
            unique_jobs.append(job)
            seen_this_run.add(jid)

    # filter already sent
    new_jobs = [j for j in unique_jobs if str(j.get("id","")).lower() not in seen]
    print(f"\nTotal: {len(all_jobs)} | Unique: {len(unique_jobs)} | New: {len(new_jobs)}")

    if not new_jobs:
        print("No new jobs to send.")
        send_telegram("✅ <b>Search complete.</b> No new jobs found this round.")
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

    # send jobs by category
    for cat, cat_jobs in sorted(grouped.items()):
        em = EMOJI.get(cat, "💻")
        send_telegram(f"━━━━━━━━━━━━━━━━\n{em} <b>{cat}</b> — {len(cat_jobs)} jobs")
        for job in cat_jobs:
            send_telegram(
                f"💼 <b>{job.get('title','')}</b>\n"
                f"🏢 {job.get('company','')}\n"
                f"📍 {job.get('location','Dublin')}\n"
                f"💰 {job.get('salary') or 'Not specified'}\n"
                f"📅 {job.get('posted','')}\n"
                f"🔗 <a href='{job.get('url','')}'>Apply now</a>"
            )
            seen.add(str(job.get("id","")).lower())
            print(f"  Sent: {job.get('title')} @ {job.get('company')}")

    save_seen(seen)
    send_telegram(f"✅ <b>Done!</b> Sent {len(new_jobs)} new jobs. Next run in 30 mins.")
    print(f"\n[{datetime.now()}] Done — sent {len(new_jobs)} jobs.")

if __name__ == "__main__":
    main()
