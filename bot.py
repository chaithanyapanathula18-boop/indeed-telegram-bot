import os
import json
import requests
import time

APIFY_TOKEN = os.environ["APIFY_TOKEN"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# Use dataset instead of local file (GitHub resets files every run)
DATASET_URL = "https://api.apify.com/v2/key-value-stores/default/records/seen_jobs?token=" + APIFY_TOKEN

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
# Load seen jobs from Apify KV store
# -------------------------
def load_seen_jobs():
        try:
                    res = requests.get(DATASET_URL)
                    if res.status_code == 200:
                                    data = res.json()
                                    if isinstance(data, list):
                                                        return data
                                            except:
                                pass
    return []

# -------------------------
# Save seen jobs
# -------------------------
def save_seen_jobs(seen_jobs):
        requests.put(DATASET_URL, json=seen_jobs)

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
                res = requests.post(url, json=payload, timeout=120)
        data = res.json()
        if isinstance(data, list):
                        return data
                except:
        pass
    return []

# -------------------------
# Send Telegram
# -------------------------
def send_telegram(msg):
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={
                "chat_id": CHAT_ID,
                "text": msg,
                "disable_web_page_preview": True
    })

# -------------------------
# Main logic
# -------------------------
def main():
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

            # Skip duplicates
            if job_id in new_seen:
                                continue

            message = f"""
            \U0001f680 {job.get('positionName') or job.get('title')}
            \U0001f3e2 {job.get('company') or job.get('companyName')}
            \U0001f4cd {job.get('location')}

            \U0001f517 {job.get('url') or job.get('applyUrl')}
            """

            send_telegram(message)

            new_seen.add(job_id)
            sent_count += 1

            time.sleep(1)  # prevent Telegram rate limit

            if sent_count >= MAX_PER_RUN:
                                break

        if sent_count >= MAX_PER_RUN:
                        break

    # Save updated seen jobs
    save_seen_jobs(list(new_seen))


if __name__ == "__main__":
        main()
