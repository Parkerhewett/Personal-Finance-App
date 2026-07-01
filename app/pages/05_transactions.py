"""Raw transaction explorer."""

import streamlit as st

from utils.config import APP_TITLE
from utils.db import run_query
from utils.formatting import money

st.set_page_config(page_title=f"Transactions · {APP_TITLE}",
                   page_icon="🔍", layout="wide")

st.title("🔍 Transactions")
st.caption("Search and filter every transaction.")


# -----------------------------------------------------------------------------
# Load filter options
# -----------------------------------------------------------------------------
groups = run_query("""
    SELECT DISTINCT category_group
    FROM finance.silver.everydollar_transactions
    WHERE category_group IS NOT NULL
    ORDER BY category_group
""")["category_group"].tolist()

months = run_query("""
    SELECT DISTINCT year_month
    FROM finance.silver.everydollar_transactions
    ORDER BY year_month DESC
""")["year_month"].tolist()


# -----------------------------------------------------------------------------
# Sidebar filters
# -----------------------------------------------------------------------------
with st.sidebar:
    st.subheader("🎛️ Filters")
    sel_months  = st.multiselect("Months",          months, default=months)
    sel_groups  = st.multiselect("Category Groups", groups, default=groups)
    flow_filter = st.radio(
        "Flow type",
        ["All", "Expenses only", "Income only", "Exclude transfers"],
        index=3,
    )
    search = st.text_input("Merchant search", "")


# -----------------------------------------------------------------------------
# Build WHERE clause (broken into separate steps to avoid nested f-strings)
# -----------------------------------------------------------------------------
clauses = ["1=1"]

if sel_months:
    months_list = ",".join(f"'{m}'" for m in sel_months)
    clauses.append(f"year_month IN ({months_list})")

if sel_groups:
    groups_list = ",".join(f"'{g}'" for g in sel_groups)
    clauses.append(f"category_group IN ({groups_list})")

if   flow_filter == "Expenses only":     clauses.append("flow_category = 'expense'")
elif flow_filter == "Income only":        clauses.append("flow_category = 'income'")
elif flow_filter == "Exclude transfers":  clauses.append("is_transfer = false")

if search:
    safe = search.replace("'", "''")
    clauses.append(f"LOWER(merchant_clean) LIKE LOWER('%{safe}%')")

where = " AND ".join(clauses)


# -----------------------------------------------------------------------------
# Run the query — THIS is where 'txns' gets created
# -----------------------------------------------------------------------------
txns = run_query(f"""
    SELECT
        transaction_date,
        category_group,
        category_item,
        merchant_clean,
        amount,
        amount_abs,
        flow_category,
        note
    FROM finance.silver.everydollar_transactions
    WHERE {where}
    ORDER BY transaction_date DESC, amount_abs DESC
""")


# -----------------------------------------------------------------------------
# Summary metrics
# -----------------------------------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Transactions",  f"{len(txns):,}")
c2.metric(
    "Total inflow",
    money(txns.loc[txns["flow_category"] == "income",  "amount_abs"].sum()),
)
c3.metric(
    "Total outflow",
    money(txns.loc[txns["flow_category"] == "expense", "amount_abs"].sum()),
)


# -----------------------------------------------------------------------------
# Display table
# -----------------------------------------------------------------------------
st.divider()
st.dataframe(txns, hide_index=True, use_container_width=True)
st.caption(f"Showing {len(txns):,} transactions matching your filters.")
