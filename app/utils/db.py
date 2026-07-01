"""Databricks SQL warehouse connection + query helpers."""

import os
import pandas as pd
import streamlit as st
from databricks import sql
from databricks.sdk.core import Config


# -----------------------------------------------------------------------------
# Connection
# -----------------------------------------------------------------------------
def _get_http_path() -> str:
    """
    Pulls SQL warehouse HTTP path.

    Strategy:
      1. Check standard env vars (warehouse ID or full path)
      2. Fall back to discovering the first warehouse the app has access to
         using the Databricks SDK (works as long as a warehouse resource is
         attached with CAN USE permission).
    """
    # Strategy 1: explicit env vars
    http_path = (
        os.getenv("SQL_WAREHOUSE_HTTP_PATH")
        or os.getenv("DATABRICKS_HTTP_PATH")
    )
    if http_path:
        return http_path

    warehouse_id = (
        os.getenv("DATABRICKS_WAREHOUSE_ID")
        or os.getenv("sql_warehouse")            # matches your resource key
        or os.getenv("DATABRICKS_SQL_WAREHOUSE_ID")
    )
    if warehouse_id:
        return f"/sql/1.0/warehouses/{warehouse_id}"

    # Strategy 2: discover via SDK (since the resource is attached, the app
    # has CAN USE on the warehouse — we can just ask for the list)
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        warehouses = list(w.warehouses.list())
        if warehouses:
            wh = warehouses[0]
            return f"/sql/1.0/warehouses/{wh.id}"
    except Exception as e:
        st.warning(f"SDK warehouse discovery failed: {e}")

    # Strategy 3: give up loudly with debug info
    available = sorted([k for k in os.environ.keys()
                        if any(t in k.upper() for t in ["DATABRICKS", "SQL", "WAREHOUSE"])])
    st.error(
        "⚠️ No SQL warehouse configured. In the Databricks Apps UI, "
        "attach a SQL warehouse resource to this app, then redeploy."
    )
    st.info(f"🔍 Detected related env vars: {available}")
    st.stop()

def execute_write(query: str) -> None:
    """
    Execute a write operation (INSERT/UPDATE/DELETE/MERGE).
    Clears cache so subsequent reads see fresh data.
    """
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
    st.cache_data.clear()

def _get_connection():
    """
    Returns an authenticated Databricks SQL connection using the app's
    service principal (no tokens needed — Databricks handles auth).
    """
    cfg = Config()
    server_hostname = cfg.host.replace("https://", "").replace("http://", "")

    return sql.connect(
        server_hostname=server_hostname,
        http_path=_get_http_path(),
        credentials_provider=lambda: cfg.authenticate,
        _use_arrow_native_complex_types=False,
    )


# -----------------------------------------------------------------------------
# Query helpers — these are what your pages actually call
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner="Querying Databricks...")
def run_query(query: str) -> pd.DataFrame:
    """
    Execute a SQL query and return results as a pandas DataFrame.

    Cached for 10 minutes per unique query string — avoids hammering the
    warehouse if multiple components on the same page need the same data.

    Args:
        query: A valid Spark SQL query string.

    Returns:
        pandas.DataFrame with the query results.
    """
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall_arrow().to_pandas()


@st.cache_data(ttl=600)
def load_table(table_name: str, where: str | None = None,
               order_by: str | None = None, limit: int | None = None) -> pd.DataFrame:
    """
    Convenience wrapper to SELECT * from a table with optional filters.

    Examples:
        load_table("finance.gold.savings_rate")
        load_table("finance.gold.monthly_cashflow", where="year = 2026")
        load_table("finance.silver.everydollar_transactions",
                   where="is_transfer = false",
                   order_by="transaction_date DESC", limit=100)
    """
    q = f"SELECT * FROM {table_name}"
    if where:    q += f" WHERE {where}"
    if order_by: q += f" ORDER BY {order_by}"
    if limit:    q += f" LIMIT {limit}"
    return run_query(q)


def clear_cache():
    """Manually clear all cached queries — useful after re-running pipelines."""
    st.cache_data.clear()
