import os
import pandas as pd
import snowflake.connector

def sf_conn():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )

def df_to_snowflake(df: pd.DataFrame, table: str):
    conn = sf_conn(); cs = conn.cursor()
    try:
        cols = ", ".join(f'"{c}"' for c in df.columns)
        cs.execute(f'create table if not exists "{table}" ({", ".join([f\'"{c}" string\' for c in df.columns])})')
        cs.executemany(
            f'insert into "{table}" ({cols}) values ({", ".join(["%s"]*len(df.columns))})',
            [tuple(None if pd.isna(v) else str(v) for v in row) for _, row in df.iterrows()]
        )
        conn.commit()
    finally:
        cs.close(); conn.close()

def snowflake_query(sql: str) -> pd.DataFrame:
    conn = sf_conn()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()
