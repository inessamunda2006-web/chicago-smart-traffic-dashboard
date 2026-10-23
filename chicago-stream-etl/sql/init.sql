CREATE TABLE IF NOT EXISTS crime (
    id BIGINT PRIMARY KEY,
    case_number TEXT,
    timestamp TIMESTAMP,
    block TEXT,
    iucr TEXT,
    primary_type TEXT,
    description TEXT,
    location_description TEXT,
    arrest BOOLEAN,
    domestic BOOLEAN,
    beat TEXT,
    district TEXT,
    ward INTEGER,
    community_area INTEGER,
    year INTEGER,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    location TEXT
);

CREATE TABLE IF NOT EXISTS accident (
    crash_record_id TEXT PRIMARY KEY,
    crash_date TIMESTAMP,
    posted_speed_limit INTEGER,
    weather_condition TEXT,
    lighting_condition TEXT,
    first_crash_type TEXT,
    trafficway_type TEXT,
    roadway_surface_cond TEXT,
    road_defect TEXT,
    crash_type TEXT,
    hit_and_run_i TEXT,
    damage TEXT,
    prim_contributory_cause TEXT,
    street_name TEXT,
    num_units INTEGER,
    crash_month INTEGER,
    most_severe_injury TEXT,
    injuries_total INTEGER,
    injuries_fatal INTEGER,
    crash_hour INTEGER,
    crash_day_of_week INTEGER,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    location TEXT
);

CREATE TABLE IF NOT EXISTS traffic (
    segmentid INTEGER,
    street TEXT,
    direction TEXT,
    from_street TEXT,
    to_street TEXT,
    length DOUBLE PRECISION,
    start_lon DOUBLE PRECISION,
    start_lat DOUBLE PRECISION,
    end_lon DOUBLE PRECISION,
    end_lat DOUBLE PRECISION,
    traffic INTEGER,
    last_updated TIMESTAMP,
    PRIMARY KEY (segmentid, last_updated)
);

CREATE TABLE IF NOT EXISTS pollution (
    record_id TEXT PRIMARY KEY,
    datasourceid TEXT,
    timestamp TIMESTAMP,
    sensor_name TEXT,
    no2 DOUBLE PRECISION,
    pm2_5 DOUBLE PRECISION,
    ambient_humidity DOUBLE PRECISION,
    ambient_temperature DOUBLE PRECISION,
    internal_humidity DOUBLE PRECISION,
    internal_temperature DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    location TEXT
);

CREATE TABLE IF NOT EXISTS ingest_state (
    dataset TEXT PRIMARY KEY,
    watermark TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);
