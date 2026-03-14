import time
import subprocess
from datetime import datetime

print("🤖 Job bot scheduler started! Running every 30 minutes...\n")

while True:
    print(f"⏰ [{datetime.now()}] Running search...")
    subprocess.run(["python3", "bot.py"])
    
    print("💤 Sleeping for 30 minutes...\n")
    time.sleep(1800)  # 30 minutes in seconds
