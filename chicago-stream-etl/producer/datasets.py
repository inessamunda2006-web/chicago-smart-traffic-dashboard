BASE = "https://data.cityofchicago.org/resource"

DATASETS = {
    "crime": {
        "url": f"{BASE}/ijzp-q8t2.json",
        "topic": "chi.crime.raw",
        "key": "id",
        "cursor": "date",
        "mode": "stream",
        "page_size": 5000,
        "timeout": 60,
    },
    "accident": {
        "url": f"{BASE}/85ca-t3if.json",
        "topic": "chi.accident.raw",
        "key": "crash_record_id",
        "cursor": "crash_date",
        "mode": "stream",
        "page_size": 5000,
        "timeout": 60,
    },
    "pollution": {
        "url": f"{BASE}/xfya-dxtq.json",
        "topic": "chi.pollution.raw",
        "key": "record_id",
        "cursor": "time",
        "mode": "stream",
        "page_size": 5000,
        "timeout": 60,
        "max_rows_per_poll": 2000,
    },
    "traffic": {
        "url": f"{BASE}/4g9f-3jbs.json",
        "topic": "chi.traffic.raw",
        "key": "segment_id",
        "cursor": "time",
        "mode": "stream",
        "page_size": 5000,
        "timeout": 60,
        "max_rows_per_poll": 2000,
    },
}
