from pathlib import Path
import pandas as pd
from prefect import flow, task
from prefect_gcp.cloud_storage import GcsBucket
from prefect_gcp import GcpCredentials



@task(retries=3)
def extract_from_gcs(colour: str, year: int, month: int) -> Path:
    '''download trip data from GCS'''
    gcs_path = f"data/{colour}/{colour}_tripdata_{year}-{month:02}.parquet"
    gcs_block = GcsBucket.load("zoom-gcs")
    gcs_block.get_directory(from_path=gcs_path, local_path=f"../data/")
    return Path(f"../data/{gcs_path}")

@task()
def transform(path: Path) -> pd.DataFrame:
    ''' Data cleaning example'''

    df = pd.read_parquet(path)
    print(f"pre: missing passenger count: {df['passenger_count'].isna().sum()}")
    df['passenger_count'].fillna(0, inplace=True)
    print(f"post: missing passenger count: {df['passenger_count'].isna().sum()}")
    return df

@task()
def write_bq(df: pd.DataFrame) -> None:
    """ Write data to Big Query"""
    gcp_credentials_block = GcpCredentials.load("zoom-gcp-creds")
    df.to_gbq(
        destination_table="dezoomcampvn.rides",
        project_id="dtc-de-390106",
        credentials=gcp_credentials_block.get_credentials_from_service_account(),
        chunksize=500_000,
        if_exists="append"
    )

@flow()
def etl_gcs_to_bd():
    '''Main ETL flow to load data into BigQuery'''

    colour = "yellow"
    year = 2019
    months = [2,3]
    for month in months:
        path = extract_from_gcs(colour, year, month)
        df = transform(path)
        write_bq(df)

if __name__ == "__main__":
    etl_gcs_to_bd()
 