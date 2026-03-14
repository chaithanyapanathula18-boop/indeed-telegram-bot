import os
import json
import httpx
from datetime import datetime

TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SEEN_JOBS_FILE    = "seen_jobs.json"

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
    prompt = """Use the Indeed search tool to search for tech jobs in Dublin Ireland.

Run these searches one by one:
1. "software engineer" in Dublin, IE
2. "frontend developer" in Dublin, IE
3. "backend developer" in Dublin, IE
4. "devops engineer" in Dublin, IE
5. "data engineer" in Dublin, IE
6. "mobile developer" in Dublin, IE
7. "AI machine learning engineer" in Dublin, IE
8. "cybersecurity engineer" in Dublin, IE

After searching, return ONLY a valid JSON array like this (no markdown, no explanation, just raw JSON):
[
  {
    "id": "job_id_here",
    "title": "Job Title",
    "company": "Company Name",
    "location": "Dublin, Ireland",
    "salary": "€60,000 - €80,000",
    "posted": "March 14, 2026",
    "url": "https://apply-link.com",
    "category": "Backend"
  }
]

Category must be one of: Frontend, Backend, Fullstack, DevOps, Data, AI/ML, Mobile, Security, QA, Other.
Return ONLY the raw JSON array. No markdown fences. No explanation."""

    try:
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "mcp-client-2025-04-04",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 8000,
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
            timeout=120
        )

        data = response.json()
        print(f"Claude API status: {response.status_code}")

        # ── extract all text blocks ──────────────────────────────
        all_text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                all_text += block["text"]

        print(f"Raw response preview: {all_text[:300]}")

        if not all_text.strip():
            print("Empty response from Claude API")
            print(f"Full response: {json.dumps(data, indent=2)}")
            return []

        # ── strip markdown fences if present ────────────────────
        text = all_text.strip()
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("["):
                    text = part
                    break

        # ── find JSON array in text ──────────────────────────────
        start = text.find("[")
        end   = text.rfind("]") + 1
        if start == -1 or end == 0:
            print(f"No JSON array found in response: {text[:500]}")
            return []

        json_str = text[start:end]
        jobs = json.loads(json_str)
        print(f"Found {len(jobs)} jobs from Claude")
        return jobs

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Text was: {all_text[:500]}")
        return []
    except Exception as e:
        print(f"Claude API error: {e}")
        return []

# ── send Telegram message ────────────────────────────────────────
def send_telegram(text: str):
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

# ── category emoji map ────────────────────────────────────────────
EMOJI = {
    "Frontend":  "🎨",
    "Backend":   "⚙️",
    "Fullstack": "🔄",
    "DevOps":    "☁️",
    "Data":      "📊",
    "AI/ML":     "🤖",
    "Mobile":    "📱",
    "Security":  "🔒",
    "QA":        "🧪",
    "Other":     "💻"
}

# ── main ─────────────────────────────────────────────────────────
def main():
    print(f"[{datetime.now()}] Starting job search...")
    seen = load_seen()

    jobs = search_jobs_via_claude()

    if not jobs:
        print("No jobs returned. Check logs above.")
        return

    # filter already seen
    new_jobs = [j for j in jobs if str(j.get("id", "")) not in seen]
    print(f"New jobs (not seen before): {len(new_jobs)}")

    if not new_jobs:
        print("No new jobs to send.")
        return

    # group by category
    grouped = {}
    for job in new_jobs:
        cat = job.get("category", "Other")
        grouped.setdefault(cat, []).append(job)

    # summary message
    lines = "\n".join([
        f"  {EMOJI.get(cat,'💻')} {cat}: {len(j)}"
        for cat, j in sorted(grouped.items())
    ])
    send_telegram(
        f"🚀 <b>{len(new_jobs)} New Tech Jobs in Ireland!</b>\n"
        f"🕐 {datetime.now().strftime('%d %b %Y, %H:%M')}\n\n{lines}"
    )

    # send each category
    for category, jobs_list in sorted(grouped.items()):
        em = EMOJI.get(category, "💻")
        send_telegram(f"━━━━━━━━━━━━━━━━\n{em} <b>{category}</b> — {len(jobs_list)} jobs")

        for job in jobs_list:
            salary  = job.get("salary") or "Not specified"
            posted  = job.get("posted", "")
            url     = job.get("url", "")
            send_telegram(
                f"💼 <b>{job.get('title','N/A')}</b>\n"
                f"🏢 {job.get('company','N/A')}\n"
                f"📍 {job.get('location','Dublin')}\n"
                f"💰 {salary}\n"
                f"📅 {posted}\n"
                f"🔗 <a href='{url}'>Apply now</a>"
            )
            seen.add(str(job.get("id", "")))

    save_seen(seen)
    print(f"[{datetime.now()}] Done — sent {len(new_jobs)} jobs to Telegram.")

if __name__ == "__main__":
    main()
