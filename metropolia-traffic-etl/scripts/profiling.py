from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum, when


# Membuat Spark session
spark = (
    SparkSession.builder
    .appName("Metropolia Data Profiling")
    .getOrCreate()
)


# File yang akan diperiksa
datasets = {
    "TRAFFIC": "/opt/airflow/data/macet.csv",
    "POLLUTION": "/opt/airflow/data/polusi_udara.csv",
    "ACCIDENT": "/opt/airflow/data/kecelakaan.csv",
    "CRIME": "/opt/airflow/data/kriminalitas.csv"
}


for name, path in datasets.items():

    print("\n" + "=" * 70)
    print(f"DATASET: {name}")
    print("=" * 70)

    # ==========================
    # 1. READ DATA
    # ==========================
    df = (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .csv(path)
    )

    # ==========================
    # 2. JUMLAH BARIS & KOLOM
    # ==========================
    print(f"\nJumlah baris   : {df.count()}")
    print(f"Jumlah kolom   : {len(df.columns)}")

    # ==========================
    # 3. NAMA & TIPE KOLOM
    # ==========================
    print("\n--- Struktur Kolom ---")
    df.printSchema()

    # ==========================
    # 4. MISSING VALUE
    # ==========================
    print("\n--- Missing Value ---")

    null_counts = df.select([
        sum(
            when(
                col(f"`{c}`").isNull() | (col(f"`{c}`") == ""),
                1
            ).otherwise(0)
        ).alias(c.replace(".", "_"))
        for c in df.columns
    ])

    null_counts.show(truncate=False)

    # ==========================
    # 5. DUPLICATE
    # ==========================
    total_rows = df.count()
    distinct_rows = df.dropDuplicates().count()

    print(f"Total rows       : {total_rows}")
    print(f"Distinct rows    : {distinct_rows}")
    print(f"Duplicate rows   : {total_rows - distinct_rows}")

    # ==========================
    # 6. SAMPLE DATA
    # ==========================
    print("\n--- Sample Data ---")
    df.show(5, truncate=False)

print("\n" + "=" * 70)
print("ADDITIONAL PROFILING")
print("=" * 70)

# ==========================
# TRAFFIC
# ==========================
df_traffic = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv("/opt/airflow/data/macet.csv")
)

print("\n--- TRAFFIC VALUE DISTRIBUTION ---")
df_traffic.groupBy("_traffic").count().orderBy("_traffic").show()


# ==========================
# POLLUTION
# ==========================
df_pollution = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv("/opt/airflow/data/polusi_udara.csv")
)

print("\n--- POLLUTION STATISTICS ---")

from pyspark.sql import functions as F

df_pollution.select(
    F.col("`no2ConcIndividual.value`").alias("no2"),
    F.col("`pm2_5ConcMassIndividual.value`").alias("pm2_5")
).summary("count", "mean", "stddev", "min", "max").show()


# ==========================
# ACCIDENT
# ==========================
df_accident = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv("/opt/airflow/data/kecelakaan.csv")
)

print("\n--- ACCIDENT INJURY ---")
df_accident.groupBy("most_severe_injury").count().orderBy("count", ascending=False).show()


# ==========================
# CRIME
# ==========================
df_crime = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv("/opt/airflow/data/kriminalitas.csv")
)

print("\n--- CRIME PRIMARY TYPE ---")
df_crime.groupBy("Primary Type").count().show()

spark.stop()