import os
import requests
import time

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

KV_STORE = "job-bot-store"

DATASET_URL = f"https://api.apify.com/v2/key-value-stores/{KV_STORE}/records/seen_jobs?token={APIFY_TOKEN}"

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

ACTOR_ID = "dan.scraper/linkedin-jobs-scraper"


# -------------------------
# Load seen jobs
# -------------------------
def load_seen_jobs():
    try:
        res = requests.get(DATASET_URL, timeout=30)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list):
                print(f"[load_seen_jobs] Loaded {len(data)} jobs")
                return data
        else:
            print("[load_seen_jobs] Starting fresh")
    except Exception as e:
        print(f"[load_seen_jobs] Error: {e}")

    return []


# -------------------------
# Save seen jobs
# -------------------------
def save_seen_jobs(seen_jobs):
    try:
        requests.put(DATASET_URL, json=seen_jobs, timeout=30)
        print(f"[save_seen_jobs] Saved {len(seen_jobs)} jobs")
    except Exception as e:
        print(f"[save_seen_jobs] Error: {e}")


# -------------------------
# Fetch jobs using correct Apify flow
# -------------------------
def fetch_jobs(search):
    run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_TOKEN}"

    payload = {
        "keywords": search,
        "location": "Ireland",
        "maxItems": 10
    }

    try:
        print(f"[fetch_jobs] Running actor: {search}")

        # 1️⃣ Start run
        run_res = requests.post(run_url, json=payload, timeout=60)
        run_data = run_res.json()

        dataset_id = run_data.get("data", {}).get("defaultDatasetId")

        if not dataset_id:
            print("[fetch_jobs] No dataset ID")
            return []

        print(f"[fetch_jobs] Dataset: {dataset_id}")

        # 2️⃣ Wait for results
        time.sleep(10)

        # 3️⃣ Fetch dataset
        dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}"

        data_res = requests.get(dataset_url, timeout=60)

        if data_res.status_code != 200:
            print("[fetch_jobs] Failed dataset fetch:", data_res.text)
            return []

        jobs = data_res.json()

        print(f"[fetch_jobs] Found {len(jobs)} jobs")

        return jobs

    except Exception as e:
        print(f"[fetch_jobs] Error: {e}")

    return []


# -------------------------
# Send Telegram
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

        if res.status_code == 200:
            print("[telegram] sent")
        else:
            print("[telegram] failed:", res.text)

    except Exception as e:
        print(f"[telegram] error: {e}")


# -------------------------
# Main
# -------------------------
def main():
    print("=== JOB BOT START ===")

    seen_jobs = load_seen_jobs()
    new_seen = set(seen_jobs)

    sent_count = 0
    MAX_PER_RUN = 20

    for search in SEARCHES:
        jobs = fetch_jobs(search)

        for job in jobs:
            if not isinstance(job, dict):
                continue

            job_id = job.get("id") or job.get("applyUrl") or job.get("url")

            if not job_id:
                continue

            if job_id in new_seen:
                continue

            title = job.get("title") or "N/A"
            company = job.get("companyName") or "N/A"
            location = job.get("location") or "N/A"
            link = job.get("applyUrl") or job.get("url") or "N/A"

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

    save_seen_jobs(list(new_seen))

    print(f"=== DONE: sent {sent_count} jobs ===")


if __name__ == "__main__":
    main()
