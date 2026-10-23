import json
import os
import signal
import sys
import time
from collections import defaultdict

import psycopg2
from psycopg2.extras import execute_values
from kafka import KafkaConsumer, KafkaProducer

from transforms import TABLES


KAFKA_BROKER = os.getenv(
    "KAFKA_BROKER",
    "kafka:9092",
)

GROUP_ID = os.getenv(
    "CONSUMER_GROUP",
    "chicago-processor",
)

BATCH_SIZE = int(
    os.getenv("BATCH_SIZE", "2000")
)

DLQ_TOPIC = "chi.dlq"


DB = dict(
    host=os.getenv("DB_HOST", "postgres"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
)


stopping = False


def log(msg):
    print(f"[PROCESSOR] {msg}", flush=True)


def on_signal(signum, frame):
    global stopping
    stopping = True


def connect_db():
    while True:
        try:
            conn = psycopg2.connect(**DB)

            log("connected to Postgres")

            return conn

        except Exception as e:
            log(
                f"Postgres not ready, retry in 3s ({e})"
            )
            time.sleep(3)


def ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            "ALTER TABLE pollution "
            "ADD COLUMN IF NOT EXISTS "
            "internal_humidity DOUBLE PRECISION, "
            "ADD COLUMN IF NOT EXISTS "
            "internal_temperature DOUBLE PRECISION"
        )

    conn.commit()


def connect_kafka():
    while True:
        try:
            consumer = KafkaConsumer(
                *list(TABLES),
                bootstrap_servers=[KAFKA_BROKER],
                group_id=GROUP_ID,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                max_poll_records=BATCH_SIZE,
                api_version=(2, 5, 0),
            )

            dlq = KafkaProducer(
                bootstrap_servers=[KAFKA_BROKER],
                acks="all",
                api_version=(2, 5, 0),
            )

            log("connected to Kafka")

            return consumer, dlq

        except Exception as e:
            log(
                f"Kafka not ready, retry in 3s ({e})"
            )
            time.sleep(3)


def upsert(cur, spec, rows):
    cols = spec["columns"]
    pk = spec["pk"]

    unique = {}

    for row in rows:
        unique[
            tuple(row[c] for c in pk)
        ] = row

    values = [
        tuple(row[c] for c in cols)
        for row in unique.values()
    ]

    col_sql = ", ".join(
        f'"{c}"'
        for c in cols
    )

    pk_sql = ", ".join(
        f'"{c}"'
        for c in pk
    )

    updates = ", ".join(
        f'"{c}" = EXCLUDED."{c}"'
        for c in cols
        if c not in pk
    )

    sql = (
        f'INSERT INTO {spec["table"]} '
        f'({col_sql}) VALUES %s '
        f'ON CONFLICT ({pk_sql}) '
        f'DO UPDATE SET {updates}'
    )

    execute_values(
        cur,
        sql,
        values,
        page_size=1000,
    )

    return len(values)


def process(batch, conn, dlq):
    by_topic = defaultdict(list)

    for tp, messages in batch.items():
        by_topic[tp.topic].extend(messages)

    counts = {}
    bad = 0

    with conn.cursor() as cur:

        for topic, messages in by_topic.items():

            spec = TABLES.get(topic)

            if spec is None:
                continue

            good = []

            for message in messages:
                try:
                    good.append(
                        spec["transform"](
                            json.loads(
                                message.value
                            )
                        )
                    )

                except Exception as e:
                    bad += 1

                    dlq.send(
                        DLQ_TOPIC,
                        key=message.key,
                        value=json.dumps(
                            {
                                "topic": topic,
                                "offset": message.offset,
                                "error": str(e),
                                "raw": message.value.decode(
                                    "utf-8",
                                    "replace",
                                ),
                            }
                        ).encode("utf-8"),
                    )

            if good:
                counts[
                    spec["table"]
                ] = upsert(
                    cur,
                    spec,
                    good,
                )

    conn.commit()

    return counts, bad


def main():
    signal.signal(
        signal.SIGTERM,
        on_signal,
    )

    signal.signal(
        signal.SIGINT,
        on_signal,
    )

    conn = connect_db()

    ensure_schema(conn)

    consumer, dlq = connect_kafka()

    log("ready")

    while not stopping:

        batch = consumer.poll(
            timeout_ms=1000,
            max_records=BATCH_SIZE,
        )

        if not batch:
            continue

        try:
            counts, bad = process(
                batch,
                conn,
                dlq,
            )

            dlq.flush()

            consumer.commit()

        except Exception as e:
            log(
                f"batch failed, "
                f"exiting for restart: {e}"
            )

            try:
                conn.rollback()
            except Exception:
                pass

            sys.exit(1)

        log(
            f"upserted={counts} "
            f"dlq={bad}"
        )

    consumer.close()
    conn.close()

    log("stopped")


if __name__ == "__main__":
    main()
