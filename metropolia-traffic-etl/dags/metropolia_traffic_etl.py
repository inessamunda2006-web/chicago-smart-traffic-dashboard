
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="metropolia_traffic_etl",
    start_date=datetime(2026, 9, 21),
    schedule=timedelta(minutes=15),
    catchup=False,
    max_active_runs=1,
    tags=["metropolia", "traffic", "etl", "pyspark"],
) as dag:

    fetch_traffic_api = BashOperator(
        task_id="fetch_traffic_api",
        bash_command=(
            "python /opt/airflow/scripts/etch_traffic_api.py"
        ),
    )

    profiling = BashOperator(
        task_id="profiling",
        bash_command=(
            "python /opt/airflow/scripts/profiling.py"
        ),
    )

    transformation = BashOperator(
        task_id="transformation",
        bash_command=(
            "python /opt/airflow/scripts/transform.py"
        ),
    )

    load = BashOperator(
        task_id="load",
        bash_command=(
            "python /opt/airflow/scripts/load.py"
        ),
    )

    fetch_traffic_api >> profiling >> transformation >> load
