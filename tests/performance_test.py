
import os
import time
import statistics
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load the same .env file used by main.py
load_dotenv(
    Path(__file__).resolve().parent.parent
    / "backend" / ".env"
)

API_KEY = os.getenv("SMART_BIN_API_KEY")

URL = "http://127.0.0.1:8000/api/readings"

if not API_KEY:
    raise RuntimeError(
        "SMART_BIN_API_KEY is missing from your .env file"
    )

# Match the authentication method in main.py
headers = {
    "X-API-Key": API_KEY
}

# Must match ReadingInput in main.py
payload = {
    "device_id": 1,
    "raw_distance_cm": 10
}

response_times = []
success_count = 0
failure_count = 0

for i in range(100):
    start = time.perf_counter()

    try:
        response = requests.post(
            URL,
            json=payload,
            headers=headers,
            timeout=5
        )

        elapsed = (time.perf_counter() - start) * 1000

        if 200 <= response.status_code < 300:
            success_count += 1
            response_times.append(elapsed)
        else:
            failure_count += 1
            print(
                f"Request {i + 1}: "
                f"HTTP {response.status_code} - "
                f"{response.text}"
            )

    except requests.RequestException as error:
        failure_count += 1
        print(f"Request {i + 1} failed: {error}")

print("\n--- PERFORMANCE TEST RESULTS ---")
print("Total requests:", 100)
print("Successful:", success_count)
print("Failed:", failure_count)

if response_times:
    print(
        f"Average response: "
        f"{statistics.mean(response_times):.2f} ms"
    )
    print(
        f"Maximum response: {max(response_times):.2f} ms"
    )
    print(
        f"Minimum response: {min(response_times):.2f} ms"
    )
