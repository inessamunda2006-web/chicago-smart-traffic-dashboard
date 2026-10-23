"""Fixed-anchor Chicago Open Data -> Kafka producer.

Source event time starts on 2026-02-15 at the local time-of-day the process
starts, then advances at real wall-clock speed (1 real second = 1 source
second). There is no backfill: each dataset begins with an empty window.
"""

import json
import os
import signal
import threading
import time
from datetime import datetime, timedelta

import psycopg2
import requests
from kafka import KafkaProducer

from datasets import DATASETS

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
APP_TOKEN = os.getenv("SOCRATA_APP_TOKEN", "")

PAGE_SIZE = int(os.getenv("PAGE_SIZE", "5000"))
STREAM_POLL_SECONDS = float(os.getenv("STREAM_POLL_SECONDS", "2"))

LOCAL_UTC_OFFSET_HOURS = float(os.getenv("LOCAL_UTC_OFFSET_HOURS", "0"))
STREAM_DATE = datetime.strptime(os.getenv("STREAM_DATE") or "2026-02-15", "%Y-%m-%d").date()
RUN_STARTED = datetime.utcnow()
_fixed = os.getenv("STREAM_START_TIME", "")
_local_time_of_day = (
    datetime.strptime(_fixed, "%H:%M:%S").time()
    if _fixed
    else (RUN_STARTED + timedelta(hours=LOCAL_UTC_OFFSET_HOURS)).time()
)
STREAM_START = datetime.combine(STREAM_DATE, _local_time_of_day)

RETRY_STATUS = (429, 500, 502, 503, 504)

TS_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
)

DB = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

stop = threading.Event()
thread_local = threading.local()


def log(message):
    print(f"[PRODUCER] {message}", flush=True)


def parse_ts(value):
    if isinstance(value, datetime):
        return value
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported timestamp: {value!r}")


def fmt_ts(value):
    return value.isoformat(timespec="milliseconds")


def source_now():
    """Current position of the simulated source clock."""
    return STREAM_START + (datetime.utcnow() - RUN_STARTED)


def db():
    conn = getattr(thread_local, "conn", None)
    if conn is None or conn.closed:
        conn = psycopg2.connect(**DB)
        conn.autocommit = True
        thread_local.conn = conn
    return conn


def get_watermark(dataset):
    with db().cursor() as cur:
        cur.execute(
            "SELECT watermark FROM ingest_state WHERE dataset = %s",
            (dataset,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def set_watermark(dataset, value):
    with db().cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingest_state (dataset, watermark, updated_at)
            VALUES (%s, %s, now())
            ON CONFLICT (dataset) DO UPDATE SET
                watermark = EXCLUDED.watermark,
                updated_at = now()
            """,
            (dataset, value),
        )


def get_rows(cfg, params):
    headers = {"X-App-Token": APP_TOKEN} if APP_TOKEN else {}
    last_error = None
    for attempt in range(4):
        try:
            response = requests.get(
                cfg["url"], params=params, headers=headers, timeout=cfg.get("timeout", 60),
            )
            log(f"HTTP {response.status_code} ({cfg['url'].rsplit('/', 1)[-1]})")
            if response.status_code in RETRY_STATUS:
                last_error = RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
                time.sleep(min(2 ** attempt, 15))
                continue
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            time.sleep(min(2 ** attempt, 15))
    raise last_error or RuntimeError("Socrata request failed")


def clean(row):
    return {key: value for key, value in row.items() if not key.startswith(":")}


def fetch_pages(cfg, start, end):
    cursor = cfg["cursor"]
    key = cfg["key"]
    page_size = cfg.get("page_size", PAGE_SIZE)
    last_cursor = None
    last_key = None

    while True:
        clauses = []
        if start is not None:
            clauses.append(f"{cursor} >= '{fmt_ts(start)}'")
        if end is not None:
            clauses.append(f"{cursor} < '{fmt_ts(end)}'")
        if last_cursor is not None:
            safe_cursor = str(last_cursor).replace("'", "''")
            safe_key = str(last_key).replace("'", "''")
            clauses.append(
                f"({cursor} > '{safe_cursor}' OR "
                f"({cursor} = '{safe_cursor}' AND {key} > '{safe_key}'))"
            )

        params = {"$limit": page_size, "$order": f"{cursor} ASC, {key} ASC"}
        if clauses:
            params["$where"] = " AND ".join(f"({c})" for c in clauses)

        rows = get_rows(cfg, params)
        if not rows:
            return
        yield rows

        last_cursor = rows[-1].get(cursor)
        last_key = rows[-1].get(key)
        if last_cursor is None or last_key is None:
            raise RuntimeError(f"Pagination row missing {cursor} or {key}")
        if len(rows) < page_size:
            return


def publish(producer, topic, dataset, row, ingested_at):
    key = row.get(DATASETS[dataset]["key"])
    if key is None:
        log(f"{dataset}: skipping record without primary key")
        return None

    return producer.send(
        topic,
        key=str(key).encode("utf-8"),
        value=json.dumps(clean(row), separators=(",", ":")).encode("utf-8"),
        headers=[
            ("source", dataset.encode()),
            ("ingested_at", ingested_at.encode()),
        ],
    )

def stream_time_dataset(name, cfg, producer):
    """Advance source event time from STREAM_START at wall-clock speed."""
    checkpoint = get_watermark(name)
    now = source_now()
    max_rows = cfg.get("max_rows_per_poll")

    if checkpoint:
        source_cursor = parse_ts(checkpoint) + timedelta(milliseconds=1)
    else:
        source_cursor = STREAM_START
        log(f"{name}: starting stream at {fmt_ts(STREAM_START)} (no backfill)")

    if source_cursor > now:
        source_cursor = now
    if source_cursor >= now:
        set_watermark(name, fmt_ts(now))
        return

    sent = 0
    capped = False
    ingested_at = datetime.utcnow().isoformat(timespec="milliseconds")

    for rows in fetch_pages(cfg, source_cursor, now):
        futures = []
        for row in rows:
            future = publish(producer, cfg["topic"], name, row, ingested_at)
            if future is not None:
                futures.append(future)
                sent += 1

        producer.flush()

        failed = [f for f in futures if f.exception is not None]
        if failed:
            raise RuntimeError(f"{len(failed)} sends failed for {name}")

        last_cursor = parse_ts(rows[-1][cfg["cursor"]])
        set_watermark(name, fmt_ts(last_cursor))

        if max_rows and sent >= max_rows:
            capped = True
            break

    set_watermark(name, fmt_ts(now) if not capped else fmt_ts(last_cursor))
    suffix = " (capped, resuming next poll)" if capped else ""
    log(f"{name}: emitted {sent} events; source time={fmt_ts(now)}{suffix}")

def worker(name, cfg, producer):
    while not stop.is_set():
        started = time.monotonic()
        try:
            stream_time_dataset(name, cfg, producer)
        except Exception as exc:
            log(f"{name}: stream read failed: {exc}")
        elapsed = time.monotonic() - started
        stop.wait(max(0.0, STREAM_POLL_SECONDS - elapsed))


def main():
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    while not stop.is_set():
        try:
            producer = KafkaProducer(
                bootstrap_servers=[KAFKA_BROKER],
                acks="all",
                retries=5,
                linger_ms=0,
                compression_type="gzip",
            )
            break
        except Exception as exc:
            log(f"Kafka unavailable; retrying: {exc}")
            stop.wait(3)
    else:
        return

    log(f"stream started; source anchor={fmt_ts(STREAM_START)}; speed=1x real time")

    threads = [
        threading.Thread(target=worker, args=(name, cfg, producer), daemon=True, name=name)
        for name, cfg in DATASETS.items()
    ]
    for thread in threads:
        thread.start()

    while not stop.wait(1):
        pass

    for thread in threads:
        thread.join(timeout=10)

    producer.flush()
    producer.close()

    conn = getattr(thread_local, "conn", None)
    if conn and not conn.closed:
        conn.close()

    log("producer stopped")


if __name__ == "__main__":
    main()
