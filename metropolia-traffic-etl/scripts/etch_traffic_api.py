
import csv
import json
import os
import urllib.request

# ============================================================
# CHICAGO TRAFFIC API - DATASET BARU
# ============================================================

API_URL = (
    "https://data.cityofchicago.org/api/v3/views/"
    "gc7y-n4xa/query.json"
)

OUTPUT_PATH = "/opt/airflow/data/macet.csv"
PAGE_SIZE = 1000
MAX_PAGES = 1

# Kolom disesuaikan dengan kebutuhan transform.py
COLUMNS = [
    "segmentid",
    "street",
    "_direction",
    "_fromst",
    "_tost",
    "_length",
    "start_lon",
    "_lif_lat",
    "_lit_lon",
    "_lit_lat",
    "_traffic",
    "_last_updt",
]


def fetch_page(page_number):
    url = (
        f"{API_URL}?pageNumber={page_number}"
        f"&pageSize={PAGE_SIZE}"
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Metropolia-ETL/1.0"}
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(
                f"API request failed: HTTP {response.status}"
            )

        return json.loads(response.read().decode("utf-8"))


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    all_records = []
    page_number = 1

    while page_number <= MAX_PAGES:
        print(f"Fetching API page {page_number}...")
        records = fetch_page(page_number)

        if not records:
            break

        all_records.extend(records)

        if len(records) < PAGE_SIZE:
            break

        page_number += 1

    if not all_records:
        raise RuntimeError("API returned no traffic records.")

    # Pemetaan kolom API baru ke format transform.py
    with open(
        OUTPUT_PATH,
        "w",
        newline="",
        encoding="utf-8"
    ) as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=COLUMNS,
            extrasaction="ignore"
        )
        writer.writeheader()

        for record in all_records:
            writer.writerow({
                "segmentid": record.get("segmentid"),
                "street": record.get("roadname"),
                "_direction": record.get("direction"),
                "_fromst": record.get("fromsegment"),
                "_tost": record.get("tosegment"),
                "_length": "",
                "start_lon": record.get("startlon"),
                "_lif_lat": record.get("startlat"),
                "_lit_lon": record.get("endlon"),
                "_lit_lat": record.get("endlat"),
                "_traffic": record.get("vehiclecount"),
                "_last_updt": record.get("timestamp"),
            })

    print("=" * 60)
    print("TRAFFIC API FETCH COMPLETED")
    print(f"Records fetched: {len(all_records)}")
    print(f"CSV saved to: {OUTPUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
