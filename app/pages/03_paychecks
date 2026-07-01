"""Paycheck detail page."""

import streamlit as st
import pandas as pd
import plotly.express as px

from utils.config import GOLD, APP_TITLE
from utils.db import run_query
from utils.charts import _apply_theme, GROUP_COLORS, THEME
from utils.formatting import money, pct

st.set_page_config(page_title=f"Paychecks · {APP_TITLE}",
                   page_icon="💰", layout="wide")

st.title("💰 Paychecks")
st.caption("Gross-to-net breakdown and savings tracking.")


# -----------------------------------------------------------------------------
# KPI row — across all checks
# -----------------------------------------------------------------------------
summary = run_query(f"""
    SELECT
        COUNT(*)              AS check_count,
        SUM(gross_pay)        AS total_gross,
        SUM(net_pay)          AS total_net,
        AVG(savings_rate_pct) AS avg_savings_rate,
        AVG(total_savings_rate_pct) AS avg_total_savings_rate
    FROM {GOLD['savings_rate']}
""")
s = summary.iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Checks Loaded", int(s["check_count"]))
c2.metric("Total Gross",   money(s["total_gross"]))
c3.metric("Total Net",     money(s["total_net"]))
c4.metric("Avg Savings Rate", f"{float(s['avg_savings_rate']):.1f}%",
          f"{float(s['avg_total_savings_rate']):.1f}% w/ employer")

st.divider()


# -----------------------------------------------------------------------------
# Stacked bar — paycheck composition over time
# -----------------------------------------------------------------------------
st.subheader("📊 Paycheck Composition")
st.caption("Every paycheck broken down into earnings, taxes, deductions, and net.")

breakdown = run_query(f"""
    SELECT check_date, bucket_group, SUM(amount) AS amount
    FROM {GOLD['paycheck_breakdown']}
    WHERE bucket_group != 'Employer Benefits'   -- exclude employer-paid for personal view
    GROUP BY check_date, bucket_group
    ORDER BY check_date, bucket_group
""")

fig = px.bar(
    breakdown, x="check_date", y="amount", color="bucket_group",
    color_discrete_map={
        "Gross":              THEME["accent"],
        "Employee Taxes":     THEME["tax"],
        "Pre-Tax Deductions": "#A78BFA",
        "Post-Tax Deductions":"#60A5FA",
        "Net Deposits":       THEME["income"],
    },
    barmode="group",
    text_auto=".2s",
)
fig.update_layout(title="Paycheck Composition by Check Date",
                  xaxis_title="Check Date", yaxis_title="USD")
st.plotly_chart(_apply_theme(fig, 500), use_container_width=True)

st.divider()


# -----------------------------------------------------------------------------
# Savings rate trend
# -----------------------------------------------------------------------------
st.subheader("💎 Savings Rate Over Time")

savings_df = run_query(f"""
    SELECT check_date, savings_rate_pct, total_savings_rate_pct,
           pretax_savings, posttax_savings, roth_ira_deposit, employer_contributions
    FROM {GOLD['savings_rate']}
    ORDER BY check_date
""")

col1, col2 = st.columns(2)

with col1:
    fig = px.line(savings_df, x="check_date",
                  y=["savings_rate_pct", "total_savings_rate_pct"],
                  markers=True,
                  labels={"value": "Rate %", "variable": "Metric"})
    fig.update_layout(title="Savings Rate %")
    fig.update_traces(line=dict(width=3))
    st.plotly_chart(_apply_theme(fig, 400), use_container_width=True)

with col2:
    # Stacked area: where the savings dollars go
    stacked = savings_df.melt(
        id_vars=["check_date"],
        value_vars=["pretax_savings", "posttax_savings",
                    "roth_ira_deposit", "employer_contributions"],
        var_name="bucket", value_name="amount",
    )
    fig = px.area(stacked, x="check_date", y="amount", color="bucket",
                  color_discrete_map={
                      "pretax_savings":         THEME["savings"],
                      "posttax_savings":        "#60A5FA",
                      "roth_ira_deposit":       "#A78BFA",
                      "employer_contributions": THEME["income"],
                  })
    fig.update_layout(title="Savings Dollars by Bucket")
    st.plotly_chart(_apply_theme(fig, 400), use_container_width=True)

st.divider()


# -----------------------------------------------------------------------------
# Paycheck detail table
# -----------------------------------------------------------------------------
st.subheader("🔬 Paycheck Detail")

paycheck_detail = run_query("""
    SELECT
        check_date, hours_worked, gross_pay,
        employee_taxes, pre_tax_deductions, post_tax_deductions,
        net_pay, gross_pay_ytd, net_pay_ytd
    FROM finance.silver.paycheck_totals
    ORDER BY check_date DESC
""")
st.dataframe(paycheck_detail, hide_index=True, use_container_width=True)
