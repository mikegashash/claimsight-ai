# services/snowflake_io.py
import os
import pandas as pd
from typing import Optional, Dict, Any

def _get_conn():
    """Return a live Snowflake connection or None if not configured."""
    try:
        import snowflake.connector  # type: ignore
    except Exception:
        return None

    env = {
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
    }
    if not all(env.values()):
        return None

    return snowflake.connector.connect(
        user=env["user"],
        password=env["password"],
        account=env["account"],
        warehouse=env["warehouse"],
        database=env["database"],
        schema=env["schema"],
    )

def df_to_snowflake(df: pd.DataFrame, table: str) -> Dict[str, Any]:
    """
    Create table if needed and insert rows. If Snowflake isn't configured,
    return a skip status (so the API still runs in demos).
    """
    conn = _get_conn()
    if conn is None:
        return {"status": "skipped (no snowflake creds)", "table": table, "rows": len(df)}

    cols_def = ", ".join([f'"{c}" STRING' for c in df.columns])
    create_sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({cols_def})'

    # Prepare rows as tuples of strings
    rows = [tuple("" if pd.isna(v) else str(v) for v in rec) for rec in df.to_numpy()]

    placeholders = ", ".join(["%s"] * len(df.columns))
    insert_sql = f'INSERT INTO "{table}" VALUES ({placeholders})'

    cur = conn.cursor()
    try:
        cur.execute(create_sql)
        if rows:
            cur.executemany(insert_sql, rows)
        conn.commit()
        return {"status": "ok", "table": table, "rows": len(rows)}
    finally:
        cur.close()
        conn.close()

def snowflake_query(sql: str) -> pd.DataFrame:
    """
    Run a SELECT and return a DataFrame. If not configured, return empty df.
    """
    conn = _get_conn()
    if conn is None:
        return pd.DataFrame()

    cur = conn.cursor()
    try:
        cur.execute(sql)
        cols = [c[0] for c in cur.description] if cur.description else []
        data = cur.fetchall()
        return pd.DataFrame(data, columns=cols)
    finally:
        cur.close()
        conn.close()
