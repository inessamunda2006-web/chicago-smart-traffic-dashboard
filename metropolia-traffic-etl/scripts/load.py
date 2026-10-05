from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp
from pyspark.sql.types import (
    IntegerType,
    LongType,
    DoubleType,
    FloatType,
    BooleanType,
    DateType,
    TimestampType,
    DecimalType
)

import psycopg2
from psycopg2 import sql
import os
import glob
import shutil


# =========================================================
# CONFIGURATION
# =========================================================

PROCESSED_PATH = "/opt/airflow/data/processed"
TEMP_PATH = "/opt/airflow/data/load_tmp"

DB_HOST = "target-postgres"
DB_PORT = 5432
DB_NAME = "metropolia_warehouse"
DB_USER = "metropolia_user"
DB_PASSWORD = "metropolia_pass"


# =========================================================
# START SPARK
# =========================================================

spark = (
    SparkSession.builder
    .appName("Metropolia Load")
    .getOrCreate()
)


# =========================================================
# CONNECT TO POSTGRESQL
# =========================================================

conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

cursor = conn.cursor()

print("=" * 70)
print("POSTGRESQL CONNECTION SUCCESS")
print("=" * 70)


# =========================================================
# SPARK TYPE → POSTGRESQL TYPE
# =========================================================

def spark_to_postgres_type(dtype):

    if isinstance(dtype, IntegerType):
        return "INTEGER"

    elif isinstance(dtype, LongType):
        return "BIGINT"

    elif isinstance(dtype, (DoubleType, FloatType)):
        return "DOUBLE PRECISION"

    elif isinstance(dtype, BooleanType):
        return "BOOLEAN"

    elif isinstance(dtype, DateType):
        return "DATE"

    elif isinstance(dtype, TimestampType):
        return "TIMESTAMP"

    elif isinstance(dtype, DecimalType):
        return f"NUMERIC({dtype.precision},{dtype.scale})"

    else:
        return "TEXT"


# =========================================================
# LOAD DATASET
# =========================================================

def load_dataset(dataset_name):

    print("\n" + "=" * 70)
    print(f"LOADING: {dataset_name.upper()}")
    print("=" * 70)

    parquet_path = f"{PROCESSED_PATH}/{dataset_name}"
    temp_dataset_path = f"{TEMP_PATH}/{dataset_name}"

    # -----------------------------------------
    # READ PARQUET
    # -----------------------------------------

    df = spark.read.parquet(parquet_path)

    # Tambahkan waktu data dimuat ke PostgreSQL
    if dataset_name == "traffic":
        df = df.withColumn(
            "ingested_at",
            current_timestamp()
        )

    row_count = df.count()

    print(f"Rows : {row_count}")
    print(f"Cols : {len(df.columns)}")

    # -----------------------------------------
    # CREATE TABLE
    # -----------------------------------------

    column_definitions = []

    for field in df.schema.fields:

        column_name = field.name
        postgres_type = spark_to_postgres_type(field.dataType)

        column_definitions.append(
            sql.SQL("{} {}").format(
                sql.Identifier(column_name),
                sql.SQL(postgres_type)
            )
        )

    create_table_query = sql.SQL(
        "DROP TABLE IF EXISTS {}"
    ).format(
        sql.Identifier(dataset_name)
    )

    cursor.execute(create_table_query)

    create_table_query = sql.SQL(
        "CREATE TABLE {} ({})"
    ).format(
        sql.Identifier(dataset_name),
        sql.SQL(", ").join(column_definitions)
    )

    cursor.execute(create_table_query)
    conn.commit()

    print(f"Table '{dataset_name}' created.")

    # -----------------------------------------
    # WRITE TEMPORARY CSV
    # -----------------------------------------

    if os.path.exists(temp_dataset_path):
        shutil.rmtree(temp_dataset_path)

    (
        df.coalesce(1)
        .write
        .mode("overwrite")
        .option("header", "true")
        .option("quote", '"')
        .option("escape", '"')
        .csv(temp_dataset_path)
    )

    # Find generated CSV file
    csv_files = glob.glob(
        f"{temp_dataset_path}/part-*.csv"
    )

    if not csv_files:
        raise FileNotFoundError(
            f"CSV output not found for {dataset_name}"
        )

    csv_file = csv_files[0]

    print(f"Temporary CSV created: {csv_file}")

    # -----------------------------------------
    # COPY CSV → POSTGRESQL
    # -----------------------------------------

    with open(csv_file, "r", encoding="utf-8") as file:

        copy_query = sql.SQL(
            """
            COPY {} FROM STDIN
            WITH (
                FORMAT CSV,
                HEADER TRUE,
                QUOTE '"',
                ESCAPE '"',
                NULL ''
            )
            """
        ).format(
            sql.Identifier(dataset_name)
        )

        cursor.copy_expert(
            copy_query.as_string(conn),
            file
        )

    conn.commit()

    print(f"Loaded {row_count} rows into '{dataset_name}'.")

    # -----------------------------------------
    # CLEAN TEMP FILE
    # -----------------------------------------

    shutil.rmtree(temp_dataset_path)

    print(f"Temporary files removed.")


# =========================================================
# LOAD ALL DATASETS
# =========================================================

datasets = [
    "traffic",
    "pollution",
    "accident",
    "crime"
]

for dataset in datasets:
    load_dataset(dataset)


# =========================================================
# FINISH
# =========================================================

cursor.close()
conn.close()

spark.stop()

print("\n" + "=" * 70)
print("LOAD COMPLETED")
print("=" * 70)