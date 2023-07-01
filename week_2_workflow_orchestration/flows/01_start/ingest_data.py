import pandas as pd
from time import time
from datetime import timedelta
from sqlalchemy import create_engine
import os
from prefect import flow, task
from prefect.tasks import task_input_hash
import argparse
from prefect_sqlalchemy import SqlAlchemyConnector


@task(log_prints=True, retries=3, cache_key_fn=task_input_hash, cache_expiration=timedelta(days=1))
def extract_data(params):
   url = params.url
   is_big = params.is_big
   csv_name = 'output.csv'

   os.system(f"wget {url} -O {csv_name}")
   if is_big == True:
      df_iter = pd.read_csv(csv_name, iterator=True, chunksize=100000)
      df = next(df_iter)

      df.tpep_pickup_datetime = pd.to_datetime(df.tpep_pickup_datetime)
      df.tpep_dropoff_datetime = pd.to_datetime(df.tpep_dropoff_datetime)  
      return df
   
   else:
      df_iter = pd.read_csv(csv_name)
      return df_iter

@task(log_prints=True)
def transform_data(df):
   print(f"pre: missing passenger count: {df['passenger_count'].isin([0]).sum()}")
   df = df[df['passenger_count'] != 0] 
   print(f"post: missing passenger count: {df['passenger_count'].isin([0]).sum()}")
   return df


@task(log_prints=True, retries=3)
def ingest(params, df_param):
   table_name = params.table_name
   url = params.url
   is_big = params.is_big
   csv_name = 'output.csv'
   
   connection_block = SqlAlchemyConnector.load("postgres-connector")
   with connection_block.get_connection(begin=False) as engine:
      print(is_big)
      if is_big == True:
         df = df_param

         df.tpep_pickup_datetime = pd.to_datetime(df.tpep_pickup_datetime)
         df.tpep_dropoff_datetime = pd.to_datetime(df.tpep_dropoff_datetime)  

         df.head(n=0).to_sql(name=table_name, con=engine, if_exists='replace')
         df.to_sql(name=table_name, con=engine, if_exists='append')
      else:
         os.system(f"wget {url} -O {csv_name}")
         df_iter = pd.read_csv(csv_name)
         df_iter.head(n=0).to_sql(name=table_name, con=engine, if_exists='replace')
         df_iter.to_sql(name=table_name, con=engine, if_exists='append')

@flow(name='Sub Flow', log_prints=True)
def log_subflow(args):
   print("logging subflow for {}".format(args.table_name))

@flow(name='Ingest Flow')
def main():
   parser = argparse.ArgumentParser(description='Ingest CSV data to Postgres')

   parser.add_argument('--table_name', help='a table for the db postgres')
   parser.add_argument('--url', help='a url for the postgres')
   parser.add_argument('--is_big', help='big or small dataset')

   args = parser.parse_args()
   print(args.is_big)
   log_subflow(args)
   raw_data = extract_data(args)
   plain_data = transform_data(raw_data)
   print('iiiii')
   ingest(args, df_param=plain_data)

if __name__ == '__main__':
   main()



