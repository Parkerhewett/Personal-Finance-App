"""Reconciliation page — does EveryDollar match payroll?"""

import streamlit as st

from utils.config import GOLD, APP_TITLE
from utils.db import run_query
from utils.formatting import money

st.set_page_config(page_title=f"Reconciliation · {APP_TITLE}",
                   page_icon="🎯", layout="wide")

st.title("🎯 Paycheck Reconciliation")
st.caption("Verify that EveryDollar's recorded income matches your actual paychecks.")


recon = run_query(f"""
    SELECT * FROM {GOLD['paycheck_reconciliation']}
    ORDER BY check_date DESC
""")

# Status emoji
status_emoji = {
    "MATCH":                  "✅",
    "Minor variance":         "🟡",
    "INVESTIGATE":            "🔴",
    "MISSING in EveryDollar": "⚠️",
}
recon["status"] = recon["status"].apply(lambda s: f"{status_emoji.get(s, '❓')} {s}")

# KPI counts
total = len(recon)
matched = recon["status"].str.contains("MATCH").sum()
investigate = recon["status"].str.contains("INVESTIGATE|MISSING").sum()

c1, c2, c3 = st.columns(3)
c1.metric("Total Checks", total)
c2.metric("Clean Matches", int(matched))
c3.metric("Need Attention", int(investigate))

st.divider()

st.dataframe(recon, hide_index=True, use_container_width=True)

with st.expander("ℹ️ How reconciliation works"):
    st.markdown("""
    For each paycheck in payroll data, we sum any EveryDollar income transactions
    flagged as `is_paycheck_deposit = true` within ±5 days of the check date.

    - **✅ MATCH** — variance < $1
    - **🟡 Minor variance** — within $50 (could be small rounding, fees, etc.)
    - **🔴 INVESTIGATE** — variance > $50, worth checking
    - **⚠️ MISSING** — paycheck exists in payroll but nothing matching in EveryDollar
    """)
