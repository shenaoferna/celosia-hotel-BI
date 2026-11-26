"""SQL queries page: read-only queries."""

import re

import oracledb
import streamlit as st

from db import error_message, query_read_only
from ui import page_title


def sql_queries():
    page_title("SQL queries", "Read-only queries on the guest, room, season and reservation tables.")
    sql = st.text_area("SELECT query (no semicolon at the end)", height=160,
                       placeholder="SELECT ro_type, COUNT(*) FROM room GROUP BY ro_type")
    st.caption("This page can only read data. Changes are made from the app's other pages, which apply the "
               "business rules.")
    if st.button("Run", type="primary") and sql.strip():
        text = sql.strip().rstrip(";")
        if not re.match(r"^(SELECT|WITH)\b", text, re.IGNORECASE) or ";" in text:
            st.error("Only a single SELECT query is allowed.")
            return
        try:
            st.dataframe(query_read_only(text), hide_index=True)
        except oracledb.Error as e:
            st.error(error_message(e))
