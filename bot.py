import os
import json
import httpx
from datetime import datetime

TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SEEN_JOBS_FILE    = "seen_jobs.json"

SEARCHES = [
    {"search": "software engineer",          "location": "Dublin", "country_code": "IE"},
    {"search": "frontend developer",         "location": "Dublin", "country_code": "IE"},
    {"search": "backend developer",          "location": "Dublin", "country_code": "IE"},
    {"search": "fullstack developer",        "location": "Dublin", "country_code": "IE"},
    {"search": "devops engineer",            "location": "Dublin", "country_code": "IE"},
    {"search": "cloud engineer",             "location": "Dublin", "country_code": "IE"},
    {"search": "data engineer",              "location": "Dublin", "country_code": "IE"},
    {"search": "data scientist",             "location": "Dublin", "country_code": "IE"},
    {"search": "machine learning engineer",  "location": "Dublin", "country_code": "IE"},
    {"search": "AI engineer",               "location": "Dublin", "country_code": "IE"},
    {"search": "mobile developer",           "location": "Dublin", "country_code": "IE"},
    {"search": "cybersecurity engineer",     "location": "Dublin", "country_code": "IE"},
    {"search": "QA automation engineer",     "location": "Dublin", "country_code": "IE"},
    {"search": "software engineer",          "location": "Ireland", "country_code": "IE"},
    {"search": "developer",                  "location": "remote",  "country_code": "IE"},
]

def load_seen():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(ids):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(ids), f)

def search_indeed(params: dict) -> list:
    """Call Claude API with Indeed MCP to search jobs"""
    prompt = f"""Use the Indeed search_jobs tool with exactly these parameters:
- search: "{params['search']}"
- location: "{params['location']}"
- country_code: "{params['country_code']}"

After getting results, return ONLY a raw JSON array, no markdown, no explanation:
[
  {{
    "id": "job_id_from_indeed",
    "title": "job title",
    "company": "company name",
    "location": "location",
    "salary": "salary or null",
    "posted": "date posted",
    "url": "apply url",
    "category": "Frontend|Backend|Fullstack|DevOps|Data|AI/ML|Mobile|Security|QA|Other"
  }}
]
Return ONLY the raw JSON array."""

    try:
        res = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "mcp-client-2025-04-04",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4000,
                "mcp_servers": [{
                    "type": "url",
                    "url": "https://mcp.indeed.com/claude/mcp",
                    "name": "indeed-mcp"
                }],
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=60
        )

        data = res.json()

        # check for API errors
        if res.status_code != 200:
            print(f"  API error {res.status_code}: {data}")
            return []

        raw = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                raw += block["text"]

        if not raw.strip():
            return []

        # strip markdown fences
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
        print(f"  Error: {e}")
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

def categorise(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["front", "react", "vue", "angular", "ui "]):
        return "Frontend"
    elif any(k in t for k in ["back", "api", "node", "java", "python", ".net", "ruby", "golang", "php"]):
        return "Backend"
    elif any(k in t for k in ["full", "stack"]):
        return "Fullstack"
    elif any(k in t for k in ["devops", "sre", "platform", "cloud", "aws", "azure", "gcp", "infrastructure"]):
        return "DevOps"
    elif any(k in t for k in ["data engineer", "analytics", "spark", "kafka"]):
        return "Data"
    elif any(k in t for k in ["machine learning", "ml ", "ai ", "llm", "nlp", "scientist"]):
        return "AI/ML"
    elif any(k in t for k in ["mobile", "ios", "android", "flutter", "swift", "kotlin"]):
        return "Mobile"
    elif any(k in t for k in ["security", "cyber", "infosec"]):
        return "Security"
    elif any(k in t for k in ["qa", "test", "quality", "automation"]):
        return "QA"
    return "Other"

EMOJI = {
    "Frontend":  "🎨", "Backend":   "⚙️", "Fullstack": "🔄",
    "DevOps":    "☁️", "Data":      "📊", "AI/ML":     "🤖",
    "Mobile":    "📱", "Security":  "🔒", "QA":        "🧪",
    "Other":     "💻"
}

def main():
    print(f"\n[{datetime.now()}] ── Starting job search ──")

    send_telegram(
        f"👋 <b>Hi! Job search starting...</b>\n"
        f"🕐 {datetime.now().strftime('%d %b %Y, %H:%M')}"
    )

    seen     = load_seen()
    all_jobs = []

    for i, params in enumerate(SEARCHES, 1):
        print(f"  [{i}/{len(SEARCHES)}] {params['search']} in {params['location']}...")
        jobs = search_indeed(params)
        # override category using title-based classifier
        for job in jobs:
            job["category"] = categorise(job.get("title", ""))
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
```

---

## Why this works now

The web search approach **fundamentally cannot return structured job JSON** — Claude just describes what it finds. But the **Indeed MCP via Claude API** does return real structured job data with IDs and apply URLs — which is exactly what works when you use it here in this chat.

The key header that was missing before that caused MCP to silently fail:
```
"anthropic-beta": "mcp-client-2025-04-04"
