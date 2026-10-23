# Chicago Streaming ETL

Simulates a live data stream from Chicago open data:

Socrata JSON APIs -> Kafka (KRaft) -> Python processor -> PostgreSQL

## How it works

Socrata offers query APIs, not event subscriptions, so the producer replays history as a stream. Source time starts at a fixed date and time you choose in `.env` (`STREAM_DATE` and `STREAM_START_TIME`), then advances at 1x real speed (one real second = one source second). Each dataset starts with an empty window and records are published as source time reaches them.

Each dataset has its own producer thread. Every `STREAM_POLL_SECONDS` it queries only the newly elapsed source-time slice and publishes each record to Kafka. The processor consumes the topics in micro-batches, transforms records, upserts them into PostgreSQL and routes bad records to `chi.dlq`. Progress is checkpointed per dataset in `ingest_state`, so restarts resume where they stopped.

| Dataset | Socrata id | Cursor field | Kafka topic | Table |
|---|---|---|---|---|
| Crime | `ijzp-q8t2` | `date` | `chi.crime.raw` | `crime` |
| Accident | `85ca-t3if` | `crash_date` | `chi.accident.raw` | `accident` |
| Pollution | `xfya-dxtq` | `time` | `chi.pollution.raw` | `pollution` |
| Traffic | `4g9f-3jbs` | `time` | `chi.traffic.raw` | `traffic` |

## Quick start

Requires Docker with Compose v2 and internet access to `data.cityofchicago.org`.

```
cp .env.example .env
docker compose up -d --build
docker compose ps
docker compose logs -f producer processor
```

Confirm the start point in the producer log:

```
docker compose logs producer | grep "stream started"
```

You should see `source anchor=2026-02-18T14:00:00.000` (or whatever you set). On PowerShell, use `Select-String "stream started"` instead of `grep`.

## Choosing a replay window

The stream is only as lively as the source data at the time you pick. Crime and accident are the sparsest datasets, so choose a date and hours where both are busy. Pollution has data from 2025-07-26 and traffic up to 2026-04-30, so pick a date inside both.

Example: count crimes per hour for one day (bash; on PowerShell write `` `$ `` instead of `$`):

```
curl -s "https://data.cityofchicago.org/resource/ijzp-q8t2.json?$select=date_extract_hh(date)%20as%20hour,count(*)&$where=date%20between%20%272026-02-18T00:00:00%27%20and%20%272026-02-19T00:00:00%27&$group=hour&$order=hour"
```

For the other datasets swap the dataset id and cursor field from the table above. For per-day counts use `date_trunc_ymd(date)` and `$group=day`.

The default window, 2026-02-18 from 14:00, has roughly 39 crimes and 28 accidents per hour, plus thousands of pollution and traffic rows.

## Verify

Row counts:

```
docker compose exec postgres psql -U chicago_user -d chicago_warehouse -c "SELECT 'crime' AS dataset, COUNT(*), MAX(timestamp) FROM crime UNION ALL SELECT 'accident', COUNT(*), MAX(crash_date) FROM accident UNION ALL SELECT 'traffic', COUNT(*), MAX(last_updated) FROM traffic UNION ALL SELECT 'pollution', COUNT(*), MAX(timestamp) FROM pollution;"
```

Producer checkpoints:

```
docker compose exec postgres psql -U chicago_user -d chicago_warehouse -c "SELECT * FROM ingest_state ORDER BY dataset;"
```

Kafka offsets and consumer lag:

```
docker compose exec kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server kafka:9092 --describe --group chicago-processor
```

Dead-letter queue:

```
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic chi.dlq --from-beginning --timeout-ms 5000
```

Stable row counts do not mean the stream stopped: the processor upserts by primary key.

## Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `STREAM_DATE` | `2026-02-15` | Date to replay (`YYYY-MM-DD`). `.env.example` sets `2026-02-18` |
| `STREAM_START_TIME` | empty | Start time of day (`HH:MM:SS`). Empty means your local clock at container start. `.env.example` sets `14:00:00` |
| `LOCAL_UTC_OFFSET_HOURS` | `0` | Your UTC offset, used only when `STREAM_START_TIME` is empty. The container clock is assumed to be UTC |
| `STREAM_POLL_SECONDS` | `2` | How often each dataset checks for newly elapsed source time |
| `PAGE_SIZE` | `5000` | Default Socrata page size (per-dataset values in `producer/datasets.py`) |
| `SOCRATA_APP_TOKEN` | empty | Optional token to raise API rate limits |

Per-dataset settings (page size, timeout, `max_rows_per_poll`) live in `producer/datasets.py`.

## Stop and reset

```
docker compose down
docker compose down -v --remove-orphans
```

The first command keeps data; the second deletes the database and Kafka data, including checkpoints. After changing `STREAM_DATE` or `STREAM_START_TIME`, do the full reset, otherwise the producer resumes from the old checkpoints.

## Project layout

```
docker-compose.yml
.env.example
sql/init.sql            tables and ingest_state
producer/               Socrata -> Kafka (datasets.py, producer.py)
processor/              Kafka -> PostgreSQL (transforms.py, processor.py)
```

## Notes and limitations

- The `traffic.traffic` column stores segment speed in mph from dataset `4g9f-3jbs`.
- Pollution `ambient_*` columns may be NULL because the API samples only returned internal sensor readings; `internal_*` columns are populated.
- Datasets use different timestamp fields, so their event timelines are only loosely comparable.
- Socrata HTTP 429: increase `STREAM_POLL_SECONDS` or set `SOCRATA_APP_TOKEN`.
- Ports: PostgreSQL on host `5433`, Kafka on `29092`.