from pathlib import Path
import pandas as pd
from prefect import flow, task
from prefect_gcp.cloud_storage import GcsBucket
from prefect.tasks import task_input_hash
from datetime import timedelta

@task(retries=3, cache_expiration=timedelta(minutes=1))
def fetch(dataset_url: str) -> pd.DataFrame:
    ''' Read data from web into pandas DataFrame '''
    df = pd.read_csv(dataset_url)
    return df

@task(log_prints=True)
def clean(df: pd.DataFrame) -> pd.DataFrame:
    ''' Fix DType issues '''
    df.tpep_pickup_datetime = pd.to_datetime(df.tpep_pickup_datetime)
    df.tpep_dropoff_datetime = pd.to_datetime(df.tpep_dropoff_datetime) 
    return df

@task()
def write_local(df: pd.DataFrame, colour: str, dataset_file: str) -> Path:
    '''Write data out as parquet file'''
    path = Path(f"data/{colour}/{dataset_file}.parquet").as_posix()
    df.to_parquet(path, compression="gzip")
    return path

@task()
def write_gcs(path: Path) -> None:
    '''upload local parquet file to gg cloud storage'''
    gcp_cloud_storage_bucket_block = GcsBucket.load("zoom-gcs")
    gcp_cloud_storage_bucket_block.upload_from_path(
        from_path=f"{path}",
        to_path=path
    )
    return

@flow()
def etl_wed_to_gcs(year: int, month: int, colour: str) -> None:
    ''' Main ETL function'''
    dataset_file = f"{colour}_tripdata_{year}-{month:02}"
    dataset_url = f"https://github.com/DataTalksClub/nyc-tlc-data/releases/download/{colour}/{dataset_file}.csv.gz"

    df = fetch(dataset_url)
    df_clean = clean(df)
    path = write_local(df_clean, colour, dataset_file)
    write_gcs(path)

@flow()
def etl_parent_flow(
    months: list[int] = [2,3], year: int = 2020, colour: str= 'yellow'
    ): 
    for month in months:
        etl_wed_to_gcs(year, month, colour)

if __name__ == "__main__":
    months = [1]
    year = 2019
    colour = 'yellow'
    etl_parent_flow(months, year, colour)