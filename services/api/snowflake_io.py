import os
import snowflake.connector
import pandas as pd

def sf_conn():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),       # e.g., abcd-xy123
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),   # e.g., COMPUTE_WH
        database=os.getenv("SNOWFLAKE_DATABASE"),     # e.g., CLAIMS_DB
        schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )

def df_to_snowflake(df: pd.DataFrame, table: str):
    conn = sf_conn()
    cs = conn.cursor()
    try:
        cols = ", ".join(f'"{c}"' for c in df.columns)
        placeholders = ", ".join(["%s"] * len(df.columns))
        # create table if not exists (all strings for demo)
        cs.execute(f'create table if not exists "{table}" ({", ".join([f\'"{c}" string\' for c in df.columns])})')
        cs.executemany(
            f'insert into "{table}" ({cols}) values ({placeholders})',
            [tuple(map(lambda x: None if pd.isna(x) else str(x), row)) for _, row in df.iterrows()]
        )
        conn.commit()
    finally:
        cs.close()
        conn.close()

def snowflake_query(sql: str) -> pd.DataFrame:
    conn = sf_conn()
    try:
        df = pd.read_sql(sql, conn)
        return df
    finally:
        conn.close()
