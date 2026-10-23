from datetime import datetime


TS_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
)


def blank(value):
    return value is None or value == ""


def to_text(value):
    return None if blank(value) else str(value)


def to_float(value):
    return None if blank(value) else float(value)


def to_int(value):
    number = to_float(value)

    return None if number is None else int(number)


def to_bool(value):
    if blank(value):
        return None

    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    if text in ("true", "y", "yes", "1"):
        return True

    if text in ("false", "n", "no", "0"):
        return False

    raise ValueError(f"bad boolean: {value}")


def to_ts(value):
    if blank(value):
        return None

    text = str(value).strip()

    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass

    raise ValueError(f"bad timestamp: {value}")


def first(raw, *names):
    for name in names:
        if not blank(raw.get(name)):
            return raw[name]

    return None


def pick(raw, mapping, fn):
    return {
        dst: fn(raw.get(src))
        for dst, src in mapping.items()
    }


def same(*names):
    return {
        name: name
        for name in names
    }


def need(row, *names):
    for name in names:
        if row.get(name) is None:
            raise ValueError(
                f"missing required field: {name}"
            )

    return row


def coords(raw):
    lat = to_float(raw.get("latitude"))
    lon = to_float(raw.get("longitude"))

    loc = raw.get("location")

    if (
        (lat is None or lon is None)
        and isinstance(loc, dict)
    ):
        pair = loc.get("coordinates")

        if isinstance(pair, list) and len(pair) == 2:
            lon, lat = (
                to_float(pair[0]),
                to_float(pair[1]),
            )

        elif (
            not blank(loc.get("latitude"))
            and not blank(loc.get("longitude"))
        ):
            lat = to_float(loc["latitude"])
            lon = to_float(loc["longitude"])

    if lat is None or lon is None:
        return None, None

    if lat == 0.0 and lon == 0.0:
        return None, None

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, None

    return lat, lon


def crime(raw):
    lat, lon = coords(raw)

    row = {}

    row.update(
        pick(
            raw,
            {"id": "id"},
            to_int,
        )
    )

    row.update(
        pick(
            raw,
            same(
                "case_number",
                "block",
                "iucr",
                "primary_type",
                "description",
                "location_description",
                "beat",
                "district",
            ),
            to_text,
        )
    )

    row.update(
        pick(
            raw,
            same("arrest", "domestic"),
            to_bool,
        )
    )

    row.update(
        pick(
            raw,
            same(
                "ward",
                "community_area",
                "year",
            ),
            to_int,
        )
    )

    row["timestamp"] = to_ts(raw.get("date"))

    row["latitude"] = lat
    row["longitude"] = lon

    row["location"] = (
        None
        if lat is None
        else f"({lat}, {lon})"
    )

    return need(row, "id")


def accident(raw):
    lat, lon = coords(raw)

    row = {}

    row.update(
        pick(
            raw,
            same(
                "crash_record_id",
                "weather_condition",
                "lighting_condition",
                "first_crash_type",
                "trafficway_type",
                "roadway_surface_cond",
                "road_defect",
                "crash_type",
                "hit_and_run_i",
                "damage",
                "prim_contributory_cause",
                "street_name",
                "most_severe_injury",
            ),
            to_text,
        )
    )

    row.update(
        pick(
            raw,
            same(
                "posted_speed_limit",
                "num_units",
                "crash_month",
                "injuries_total",
                "injuries_fatal",
                "crash_hour",
                "crash_day_of_week",
            ),
            to_int,
        )
    )

    row["crash_date"] = to_ts(
        raw.get("crash_date")
    )

    row["latitude"] = lat
    row["longitude"] = lon

    row["location"] = (
        None
        if lat is None
        else f"POINT ({lon} {lat})"
    )

    return need(
        row,
        "crash_record_id",
    )


def traffic(raw):
    row = {}
    row.update(pick(raw, {"segmentid": "segment_id", "traffic": "speed"}, to_int))
    row.update(pick(raw, same("street", "direction", "from_street", "to_street"), to_text))
    row.update(pick(raw, {
        "length": "length",
        "start_lon": "start_longitude",
        "start_lat": "start_latitude",
        "end_lon": "end_longitude",
        "end_lat": "end_latitude",
    }, to_float))
    row["last_updated"] = to_ts(raw.get("time"))
    return need(row, "segmentid", "last_updated")


def pollution(raw):
    lat, lon = coords(raw)

    row = {}

    row.update(
        pick(
            raw,
            same(
                "record_id",
                "datasourceid",
                "sensor_name",
            ),
            to_text,
        )
    )

    row["timestamp"] = to_ts(
        raw.get("time")
    )

    row.update(
        pick(
            raw,
            {
                "no2": "no2concindividual_value",
                "pm2_5": "pm2_5concmassindividual_value",
                "internal_humidity":
                    "relhumidinternalindividual",
                "internal_temperature":
                    "temperatureinternalindividual",
            },
            to_float,
        )
    )

    row["ambient_humidity"] = to_float(
        first(
            raw,
            "relhumidambientindividual_value",
            "relhumidambientindividual",
        )
    )

    row["ambient_temperature"] = to_float(
        first(
            raw,
            "temperatureambientindividual_value",
            "temperatureambientindividual",
        )
    )

    row["latitude"] = lat
    row["longitude"] = lon

    row["location"] = (
        None
        if lat is None
        else f"POINT ({lon} {lat})"
    )

    return need(row, "record_id")


TABLES = {
    "chi.crime.raw": {
        "table": "crime",
        "pk": ["id"],
        "columns": [
            "id",
            "case_number",
            "timestamp",
            "block",
            "iucr",
            "primary_type",
            "description",
            "location_description",
            "arrest",
            "domestic",
            "beat",
            "district",
            "ward",
            "community_area",
            "year",
            "latitude",
            "longitude",
            "location",
        ],
        "transform": crime,
    },

    "chi.accident.raw": {
        "table": "accident",
        "pk": ["crash_record_id"],
        "columns": [
            "crash_record_id",
            "crash_date",
            "posted_speed_limit",
            "weather_condition",
            "lighting_condition",
            "first_crash_type",
            "trafficway_type",
            "roadway_surface_cond",
            "road_defect",
            "crash_type",
            "hit_and_run_i",
            "damage",
            "prim_contributory_cause",
            "street_name",
            "num_units",
            "crash_month",
            "most_severe_injury",
            "injuries_total",
            "injuries_fatal",
            "crash_hour",
            "crash_day_of_week",
            "latitude",
            "longitude",
            "location",
        ],
        "transform": accident,
    },

    "chi.traffic.raw": {
        "table": "traffic",
        "pk": ["segmentid", "last_updated"],
        "columns": [
            "segmentid",
            "street",
            "direction",
            "from_street",
            "to_street",
            "length",
            "start_lon",
            "start_lat",
            "end_lon",
            "end_lat",
            "traffic",
            "last_updated",
        ],
        "transform": traffic,
    },

    "chi.pollution.raw": {
        "table": "pollution",
        "pk": ["record_id"],
        "columns": [
            "record_id",
            "datasourceid",
            "timestamp",
            "sensor_name",
            "no2",
            "pm2_5",
            "ambient_humidity",
            "ambient_temperature",
            "internal_humidity",
            "internal_temperature",
            "latitude",
            "longitude",
            "location",
        ],
        "transform": pollution,
    },
}
