from google.cloud import bigquery
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv
import time

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils.config import forex_symbols, downloading_retries

load_dotenv()

def download_data(attempts, symbols):
    dfs = {
        'daily': None,
        'weekly': None,
        'monthly': None
    }

    for attempt in range(attempts):
        try:
            dfs['daily'] = yf.download(symbols, start="2000-01-01", interval="1d")
            dfs['weekly'] = yf.download(symbols, start="2000-01-01", interval="1wk")
            dfs['monthly'] = yf.download(symbols, start="2000-01-01", interval="1mo")
            print("All the dataframes have been successfully downloaded!")
            break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2.5)
    else:
        print("Failed to download the data after multiple attempts!")
    
    for key, df in dfs.items():
        if "Volume" in df.columns:
            df.drop(columns=["Volume"], inplace=True)
        
        df = df.reset_index()
        df.columns = [f"{col[1]}_{col[0]}" if col[1] else col[0] for col in df.columns]
        df["Date"] = pd.to_datetime(df["Date"]).dt.date

        dfs[key] = df

    return dfs


def loading_to_bigquery():
    client = bigquery.Client()

    table_ids = {
        'daily': os.getenv('BQ_DAILY_TABLE'),
        'weekly': os.getenv('BQ_WEEKLY_TABLE'),
        'monthly': os.getenv('BQ_MONTHLY_TABLE')
    }

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        ignore_unknown_values=True,
        schema=[
            bigquery.SchemaField("Date", "DATE"),
            
            bigquery.SchemaField("EURUSD=X_Close", "FLOAT"),
            bigquery.SchemaField("GBPUSD=X_Close", "FLOAT"),
            bigquery.SchemaField("JPYUSD=X_Close", "FLOAT"),
            
            bigquery.SchemaField("EURUSD=X_High", "FLOAT"),
            bigquery.SchemaField("GBPUSD=X_High", "FLOAT"),
            bigquery.SchemaField("JPYUSD=X_High", "FLOAT"),
            
            bigquery.SchemaField("EURUSD=X_Low", "FLOAT"),
            bigquery.SchemaField("GBPUSD=X_Low", "FLOAT"),
            bigquery.SchemaField("JPYUSD=X_Low", "FLOAT"),
            
            bigquery.SchemaField("EURUSD=X_Open", "FLOAT"),
            bigquery.SchemaField("GBPUSD=X_Open", "FLOAT"),
            bigquery.SchemaField("JPYUSD=X_Open", "FLOAT"),
        ],
        write_disposition="WRITE_APPEND",
    )

    dfs = download_data(downloading_retries, forex_symbols)

    for key in table_ids.keys():
        job = client.load_table_from_dataframe(dfs[key], table_ids[key], job_config=job_config)
        job.result()


    print("All the data was successfully loaded into BigQuery!")


loading_to_bigquery()