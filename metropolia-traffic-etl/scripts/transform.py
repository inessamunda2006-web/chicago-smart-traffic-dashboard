from pyspark.sql import SparkSession
from pyspark.sql import functions as F
import os

# ============================================================
# SPARK SESSION
# ============================================================

spark = (
    SparkSession.builder
    .appName("Metropolia Traffic ETL - Transformation")
    .getOrCreate()
)

# ============================================================
# PATH
# ============================================================

BASE_PATH = "/opt/airflow/data"
OUTPUT_PATH = f"{BASE_PATH}/processed"

os.makedirs(OUTPUT_PATH, exist_ok=True)

# ============================================================
# 1. TRAFFIC
# ============================================================

print("\n" + "=" * 70)
print("TRANSFORMING: TRAFFIC")
print("=" * 70)

traffic = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(f"{BASE_PATH}/macet.csv")
)

traffic_clean = traffic.select(
    "segmentid",
    "street",
    F.col("_direction").alias("direction"),
    F.col("_fromst").alias("from_street"),
    F.col("_tost").alias("to_street"),
    F.col("_length").alias("length"),
    "start_lon",
    F.col("_lif_lat").alias("start_lat"),
    F.col("_lit_lon").alias("end_lon"),
    F.col("_lit_lat").alias("end_lat"),
    F.col("_traffic").alias("traffic"),
    F.col("_last_updt").alias("last_updated")
)

traffic_clean = traffic_clean.dropDuplicates()

traffic_clean.write.mode("overwrite").parquet(
    f"{OUTPUT_PATH}/traffic"
)

print(f"Traffic rows : {traffic_clean.count()}")
print(f"Traffic cols : {len(traffic_clean.columns)}")


# ============================================================
# 2. POLLUTION
# ============================================================

print("\n" + "=" * 70)
print("TRANSFORMING: POLLUTION")
print("=" * 70)

pollution = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(f"{BASE_PATH}/polusi_udara.csv")
)

pollution_clean = pollution.select(
    "datasourceid",
    F.to_timestamp(
        "time",
        "MM/dd/yyyy hh:mm:ss a"
    ).alias("timestamp"),
    "sensor_name",

    F.col("`no2ConcIndividual.value`").alias("no2"),
    F.col("`pm2_5ConcMassIndividual.value`").alias("pm2_5"),

    F.col("`relHumidAmbientIndividual.value`").alias(
        "ambient_humidity"
    ),

    F.col("`temperatureAmbientIndividual.value`").alias(
        "ambient_temperature"
    ),

    "latitude",
    "longitude",
    "location",
    "record_id"
)

pollution_clean = pollution_clean.dropDuplicates()

pollution_clean.write.mode("overwrite").parquet(
    f"{OUTPUT_PATH}/pollution"
)

print(f"Pollution rows : {pollution_clean.count()}")
print(f"Pollution cols : {len(pollution_clean.columns)}")


# ============================================================
# 3. ACCIDENT
# ============================================================

print("\n" + "=" * 70)
print("TRANSFORMING: ACCIDENT")
print("=" * 70)

accident = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(f"{BASE_PATH}/kecelakaan.csv")
)

accident_clean = accident.select(
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
    "location"
)

accident_clean = accident_clean.dropDuplicates()

accident_clean.write.mode("overwrite").parquet(
    f"{OUTPUT_PATH}/accident"
)

print(f"Accident rows : {accident_clean.count()}")
print(f"Accident cols : {len(accident_clean.columns)}")


# ============================================================
# 4. CRIME
# ============================================================

print("\n" + "=" * 70)
print("TRANSFORMING: CRIME")
print("=" * 70)

crime = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(f"{BASE_PATH}/kriminalitas.csv")
)

crime_clean = crime.select(
    "ID",
    F.col("`Case Number`").alias("case_number"),
    F.to_timestamp(
        "Date",
        "MM/dd/yyyy hh:mm:ss a"
    ).alias("timestamp"),
    "Block",
    "IUCR",
    F.col("`Primary Type`").alias("primary_type"),
    "Description",
    F.col("`Location Description`").alias(
        "location_description"
    ),
    "Arrest",
    "Domestic",
    "Beat",
    "District",
    "Ward",
    F.col("`Community Area`").alias(
        "community_area"
    ),
    "Year",
    "Latitude",
    "Longitude",
    "Location"
)

crime_clean = crime_clean.dropDuplicates()

crime_clean.write.mode("overwrite").parquet(
    f"{OUTPUT_PATH}/crime"
)

print(f"Crime rows : {crime_clean.count()}")
print(f"Crime cols : {len(crime_clean.columns)}")


# ============================================================
# FINISH
# ============================================================

print("\n" + "=" * 70)
print("TRANSFORMATION COMPLETED")
print("=" * 70)

print("\nProcessed data saved to:")
print(OUTPUT_PATH)

spark.stop()