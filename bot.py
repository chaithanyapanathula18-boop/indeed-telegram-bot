import os
import json
import httpx
from datetime import datetime

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
INDEED_MCP_URL   = "https://mcp.indeed.com/claude/mcp"
SEEN_JOBS_FILE   = "seen_jobs.json"

# ── all tech industry searches ──────────────────────────────────
SEARCHES = [
    {"search": "software engineer",        "location": "Dublin", "country_code": "IE"},
    {"search": "frontend developer",       "location": "Dublin", "country_code": "IE"},
    {"search": "backend developer",        "location": "Dublin", "country_code": "IE"},
    {"search": "fullstack developer",      "location": "Dublin", "country_code": "IE"},
    {"search": "devops engineer",          "location": "Dublin", "country_code": "IE"},
    {"search": "cloud engineer",           "location": "Dublin", "country_code": "IE"},
    {"search": "data engineer",            "location": "Dublin", "country_code": "IE"},
    {"search": "machine learning engineer","location": "Dublin", "country_code": "IE"},
    {"search": "mobile developer",         "location": "Dublin", "country_code": "IE"},
    {"search": "QA automation engineer",   "location": "Dublin", "country_code": "IE"},
    {"search": "systems engineer",         "location": "Dublin", "country_code": "IE"},
]

def load_seen():
    """Load jobs we've already sent"""
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(ids: set):
    """Save jobs we've sent so we don't send them again"""
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(ids), f)

def search_indeed(params: dict) -> list:
    """Search Indeed using the API"""
    try:
        r = httpx.post(
            f"{INDEED_MCP_URL}/search_jobs",
            headers={"Content-Type": "application/json"},
            json=params,
            timeout=15
        )
        r.raise_for_status()
        return r.json().get("jobs", [])
    except Exception as e:
        print(f"Error searching: {e}")
        return []

def send_telegram(text: str):
    """Send message to Telegram"""
    try:
        httpx.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=10
        )
    except Exception as e:
        print(f"Telegram error: {e}")

def classify_job(title: str) -> str:
    """Classify job into category"""
    t = title.lower()
    
    if any(k in t for k in ["front", "react", "vue", "angular", "ui"]):
        return "🎨 Frontend"
    elif any(k in t for k in ["back", "api", "node", "python", "java", ".net"]):
        return "⚙️ Backend"
    elif any(k in t for k in ["full", "stack"]):
        return "🔄 Full Stack"
    elif any(k in t for k in ["devops", "cloud", "aws", "azure", "kubernetes"]):
        return "☁️ DevOps/Cloud"
    elif any(k in t for k in ["data", "analytics", "sql", "spark"]):
        return "📊 Data"
    elif any(k in t for k in ["machine learning", "ai", "ml"]):
        return "🤖 AI/ML"
    elif any(k in t for k in ["mobile", "ios", "android"]):
        return "📱 Mobile"
    elif any(k in t for k in ["qa", "test", "quality"]):
        return "🧪 QA/Testing"
    else:
        return "💻 Other"

def format_job(job: dict) -> str:
    """Format job nicely for Telegram"""
    title    = job.get("title", "N/A")
    company  = job.get("company", "N/A")
    location = job.get("location", "Dublin")
    salary   = job.get("salary") or "Not specified"
    url      = job.get("url", "")
    category = classify_job(title)

    return (
        f"{category}\n"
        f"<b>{title}</b>\n"
        f"🏢 {company}\n"
        f"📍 {location}\n"
        f"💰 {salary}\n"
        f"🔗 <a href='{url}'>Apply here</a>\n"
    )

def main():
    print(f"\n⏰ [{datetime.now()}] Starting job search...")
    
    seen     = load_seen()
    new_jobs = []

    # Search all job types
    for params in SEARCHES:
        print(f"  Searching: {params['search']}...")
        jobs = search_indeed(params)
        
        for job in jobs:
            job_id = job.get("id")
            if job_id and job_id not in seen:
                new_jobs.append(job)
                seen.add(job_id)

    if not new_jobs:
        print(f"  ✗ No new jobs found.")
        return

    print(f"  ✓ Found {len(new_jobs)} new jobs!")

    # Send to Telegram
    send_telegram(
        f"🚀 <b>{len(new_jobs)} New Tech Jobs in Dublin!</b>\n"
        f"🕐 {datetime.now().strftime('%d %b, %H:%M')}\n"
    )

    for job in new_jobs:
        send_telegram(format_job(job))
        print(f"    Sent: {job.get('title')} @ {job.get('company')}")

    save_seen(seen)
    print(f"✓ Done!\n")

if __name__ == "__main__":
    main()
    
