"""Single access point to Oracle: connection pool, reads, writes in transactions and error messages."""

from contextlib import contextmanager

import oracledb
import pandas as pd
import streamlit as st


@st.cache_resource
def get_pool():
    s = st.secrets["oracle"]
    if "lib_dir" in s:   # thick mode (Instant Client)
        oracledb.init_oracle_client(lib_dir=s["lib_dir"], config_dir=s["config_dir"])
        return oracledb.create_pool(user=s["user"], password=s["password"], dsn=s["dsn"], min=1, max=4)
    return oracledb.create_pool(   # thin mode: the wallet is passed as parameters
        user=s["user"], password=s["password"], dsn=s["dsn"], min=1, max=4,
        config_dir=s["config_dir"], wallet_location=s.get("wallet_location", s["config_dir"]),
        wallet_password=s["wallet_password"])


def query(sql, params=None):
    """SELECT -> DataFrame (lowercase column names)."""
    with get_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or {})
        columns = [d[0].lower() for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columns)


def scalar(sql, params=None):
    """SELECT that returns a single number."""
    df = query(sql, params)
    v = df.iat[0, 0] if len(df) else None
    return 0 if v is None or pd.isna(v) else v


def query_read_only(sql, limit=1000):
    """Runs a user-written SELECT inside a read-only transaction."""
    with get_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute("SET TRANSACTION READ ONLY")
        try:
            cur.execute(sql)
            columns = [d[0].lower() for d in cur.description]
            return pd.DataFrame(cur.fetchmany(limit), columns=columns)
        finally:
            conn.rollback()


def error_message(e):
    """Turns the most common Oracle errors into a clear message for the user."""
    text = str(e)
    if "ORA-02292" in text:
        return "Can't delete it: there are reservations that depend on this record."
    if "ORA-00001" in text:
        return "A record with that data already exists, and it must be unique."
    if "ORA-02290" in text:
        return "That value breaks one of the database rules."
    if "ORA-01400" in text:
        return "A required field is missing."
    if "ORA-01031" in text or "ORA-01456" in text:
        return "That operation isn't allowed here."
    if "DPY-4011" in text or "ORA-03113" in text or "ORA-03114" in text or "DPY-6005" in text:
        return "The connection to the database was lost. Reload the page and try again."
    return f"Oracle rejected the operation: {text}"


@contextmanager
def transaction():
    """INSERT/UPDATE: COMMIT if everything works, ROLLBACK if anything fails."""
    conn = get_pool().acquire()
    try:
        yield conn.cursor()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_write(sql, params, success_msg, no_change_msg=None):
    """Runs an INSERT/UPDATE/DELETE in a transaction and shows the result to the user.
    Returns True if at least one row changed."""
    try:
        with transaction() as cur:
            cur.execute(sql, params)
            rows = cur.rowcount
    except oracledb.Error as e:
        st.error(error_message(e))
        return False
    if rows:
        st.success(success_msg)
        return True
    st.warning(no_change_msg or "Nothing was changed.")
    return False
