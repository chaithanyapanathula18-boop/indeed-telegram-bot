import os
import json
import requests
import time

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

DATASET_URL = f"https://api.apify.com/v2/key-value-stores/default/records/seen_jobs?token={APIFY_TOKEN}"

SEARCHES = [
    "software engineer",
    "frontend developer",
    "backend developer",
    "full stack developer",
    "react developer",
    "angular developer",
    "node developer",
    "python developer",
    "java developer",
    "dotnet developer",
    "devops engineer",
    "cloud engineer",
    "data engineer",
    "machine learning engineer",
    "ai engineer"
]

ACTOR_ID = "misceres/indeed-scraper"


# -------------------------
# Load seen jobs
# -------------------------
def load_seen_jobs():
    try:
        res = requests.get(DATASET_URL, timeout=30)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list):
                print(f"[load_seen_jobs] Loaded {len(data)} seen jobs.")
                return data
        else:
            print(f"[load_seen_jobs] Unexpected status: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"[load_seen_jobs] Error: {e}")

    return []


# -------------------------
# Save seen jobs
# -------------------------
def save_seen_jobs(seen_jobs):
    try:
        res = requests.put(DATASET_URL, json=seen_jobs, timeout=30)
        print(f"[save_seen_jobs] Saved {len(seen_jobs)} jobs. Status: {res.status_code}")
    except Exception as e:
        print(f"[save_seen_jobs] Error: {e}")


# -------------------------
# Fetch jobs from Apify
# -------------------------
def fetch_jobs(search):
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items?token={APIFY_TOKEN}"

    payload = {
        "position": search,
        "country": "IE",
        "maxItems": 15
    }

    try:
        print(f"[fetch_jobs] Fetching jobs for: '{search}'")
        res = requests.post(url, json=payload, timeout=120)
        print(f"[fetch_jobs] Status: {res.status_code}")

        data = res.json()

        if isinstance(data, list):
            print(f"[fetch_jobs] Got {len(data)} jobs for '{search}'")
            return data
        else:
            print(f"[fetch_jobs] Unexpected response for '{search}': {data}")

    except Exception as e:
        print(f"[fetch_jobs] Error for '{search}': {e}")

    return []


# -------------------------
# Send Telegram message
# -------------------------
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        res = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": msg,
                "disable_web_page_preview": True
            },
            timeout=20
        )

        if res.status_code != 200:
            print(f"[send_telegram] Failed: {res.status_code} - {res.text}")
        else:
            print("[send_telegram] Message sent successfully.")

    except Exception as e:
        print(f"[send_telegram] Error: {e}")


# -------------------------
# Main logic
# -------------------------
def main():
    print(f"[main] CHAT_ID set: {'yes' if CHAT_ID else 'NO - MISSING!'}")
    print(f"[main] TELEGRAM_TOKEN set: {'yes' if TELEGRAM_TOKEN else 'NO - MISSING!'}")
    print(f"[main] APIFY_TOKEN set: {'yes' if APIFY_TOKEN else 'NO - MISSING!'}")

    seen_jobs = load_seen_jobs()
    new_seen = set(seen_jobs)

    sent_count = 0
    MAX_PER_RUN = 20

    for search in SEARCHES:
        jobs = fetch_jobs(search)

        for job in jobs:
            if not isinstance(job, dict):
                continue

            job_id = job.get("id") or job.get("url") or job.get("applyUrl")

            if not job_id:
                continue

            if job_id in new_seen:
                continue

            title = job.get("positionName") or job.get("title") or "N/A"
            company = job.get("company") or job.get("companyName") or "N/A"
            location = job.get("location") or "N/A"
            link = job.get("url") or job.get("applyUrl") or "N/A"

            message = (
                f"🚀 {title}\n"
                f"🏢 {company}\n"
                f"📍 {location}\n\n"
                f"🔗 {link}"
            )

            send_telegram(message)

            new_seen.add(job_id)
            sent_count += 1

            time.sleep(1)

            if sent_count >= MAX_PER_RUN:
                break

        if sent_count >= MAX_PER_RUN:
            break

    print(f"[main] Done. Sent {sent_count} new job(s).")

    save_seen_jobs(list(new_seen))


if __name__ == "__main__":
    main()
