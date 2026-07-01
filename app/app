"""
Personal Finance Dashboard — Entry point.

Navigation to other pages is automatic from the pages/ directory.
This file serves as the home/overview page.
"""

import streamlit as st
from datetime import datetime

from utils.config import APP_TITLE, APP_ICON, OWNER_NAME, GOLD
from utils.db import run_query, clear_cache
from utils.formatting import money, pct


# -----------------------------------------------------------------------------
# Page configuration — must be first Streamlit call
# -----------------------------------------------------------------------------
# 1. Update page_config
st.set_page_config(
    page_title="🏠 Home",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title(APP_TITLE)
    st.caption(f"Owner: **{OWNER_NAME}**")
    st.divider()

    st.markdown("### 📊 Navigation")
    st.caption("Use the page selector above to explore your finances.")
    st.divider()

    st.markdown("### 🛠️ Tools")
    if st.button("🔄 Refresh data", use_container_width=True,
                 help="Clear cache and re-query Databricks"):
        clear_cache()
        st.toast("Cache cleared — data will refresh on next page load.", icon="✅")

    st.divider()
    st.caption(f"Last loaded: {datetime.now().strftime('%b %d, %Y · %I:%M %p')}")


# -----------------------------------------------------------------------------
# Main content — Home / Overview
# -----------------------------------------------------------------------------
st.title(f"Welcome, {OWNER_NAME} 👋")
st.markdown(
    "Your personal finance command center, powered by Databricks. "
    "Track where every dollar comes from and where it goes."
)

st.divider()

# -----------------------------------------------------------------------------
# Net Worth hero (only shows if user has snapshots)
# -----------------------------------------------------------------------------
try:
    nw = run_query(f"SELECT * FROM {GOLD['net_worth_summary']}")
    if not nw.empty and nw["net_worth"].iloc[0] is not None:
        r = nw.iloc[0]
        as_of = r["latest_snapshot_date"].strftime("%B %d, %Y") \
                if r["latest_snapshot_date"] else "—"

        st.markdown(
            f"""
            ### 💰 As of **{as_of}**, your net worth is **{money(r['net_worth'])}**

            You have **{money(r['liquid_cash'])}** available across checking and savings,
            with **{money(r['retirement_total'])}** building in retirement and tax-advantaged
            accounts.
            """
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💵 Liquid",     money(r["liquid_cash"]))
        c2.metric("🏦 Retirement", money(r["retirement_total"]))
        c3.metric("📈 Investments", money(r["investments"]))
        if r["liabilities"] and r["liabilities"] > 0:
            c4.metric("💳 Liabilities", money(r["liabilities"]))

        st.divider()
except Exception:
    # Net worth not set up yet — silently skip the hero
    pass

# -----------------------------------------------------------------------------
# Data freshness summary — confirms everything is wired up correctly
# -----------------------------------------------------------------------------
st.subheader("📦 Data Health Check")

try:
    freshness = run_query(f"""
        SELECT 'Cashflow records'      AS metric, COUNT(*) AS value FROM {GOLD['monthly_cashflow']}
        UNION ALL SELECT 'Spending categories tracked',  COUNT(*) FROM {GOLD['spending_by_category']}
        UNION ALL SELECT 'Paychecks loaded',             COUNT(*) FROM {GOLD['savings_rate']}
        UNION ALL SELECT 'Sankey flow edges',            COUNT(*) FROM {GOLD['sankey_flows']}
    """)

    cols = st.columns(len(freshness))
    for col, (_, row) in zip(cols, freshness.iterrows()):
        col.metric(label=row["metric"], value=int(row["value"]))

    st.success("✅ Connection to Databricks SQL warehouse is healthy.")

except Exception as e:
    st.error(f"❌ Couldn't reach the data warehouse: {e}")
    st.info(
        "If this is your first run, make sure you've attached a SQL warehouse "
        "to this app in the Databricks Apps UI."
    )


st.divider()


# -----------------------------------------------------------------------------
# Quick links to pages
# -----------------------------------------------------------------------------
st.subheader("🧭 Where to next?")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        "#### 💸 Money Flow\n"
        "Visualize every dollar from paycheck to grocery bill in a single Sankey diagram."
    )
with col2:
    st.markdown(
        "#### 📊 Spending\n"
        "Category breakdowns, month-over-month trends, and your top merchants."
    )
with col3:
    st.markdown(
        "#### 💰 Paychecks\n"
        "Gross-to-net detail, deduction history, and savings rate tracking."
    )
with col4:
    st.markdown(
        "#### 🏦 Net Worth\n"
        "Log account balances and watch your total grow over time."
    )

st.caption("Pages will appear in the sidebar as you add them.")
