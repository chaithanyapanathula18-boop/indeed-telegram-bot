import os
import requests
import time

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

KV_STORE = "job-bot-store"

DATASET_URL = f"https://api.apify.com/v2/key-value-stores/{KV_STORE}/records/seen_jobs?token={APIFY_TOKEN}"

# ✅ THIS ACTOR SUPPORTS SYNC CALL
ACTOR_ID = "apify/google-jobs-scraper"

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


def load_seen_jobs():
    try:
        res = requests.get(DATASET_URL)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return []


def save_seen_jobs(seen_jobs):
    try:
        requests.put(DATASET_URL, json=seen_jobs)
    except:
        pass


# ✅ FINAL FIXED FETCH
def fetch_jobs(search):
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items?token={APIFY_TOKEN}"

    payload = {
        "query": search,
        "location": "Ireland",
        "maxItems": 10
    }

    try:
        print(f"[fetch_jobs] {search}")

        res = requests.post(url, json=payload, timeout=120)

        if res.status_code != 200:
            print(res.text)
            return []

        jobs = res.json()

        print(f"[fetch_jobs] Got {len(jobs)} jobs")

        return jobs

    except Exception as e:
        print(e)

    return []


def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        })
    except:
        pass


def main():
    print("=== START ===")

    seen_jobs = load_seen_jobs()
    new_seen = set(seen_jobs)

    for search in SEARCHES:
        jobs = fetch_jobs(search)

        for job in jobs:
            job_id = job.get("id") or job.get("url")

            if not job_id or job_id in new_seen:
                continue

            title = job.get("title", "N/A")
            company = job.get("companyName", "N/A")
            location = job.get("location", "N/A")
            link = job.get("url", "N/A")

            msg = f"🚀 {title}\n🏢 {company}\n📍 {location}\n\n🔗 {link}"

            send_telegram(msg)

            new_seen.add(job_id)
            time.sleep(1)

    save_seen_jobs(list(new_seen))

    print("=== DONE ===")


if __name__ == "__main__":
    main()
