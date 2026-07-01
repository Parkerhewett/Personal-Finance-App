"""Money Flow page — the headline visualizations."""

import streamlit as st
import pandas as pd

from utils.config import GOLD, APP_TITLE
from utils.db import run_query
from utils.charts import sankey_money_flow, waterfall_gross_to_net
from utils.formatting import money, pct

st.set_page_config(page_title=f"Money Flow · {APP_TITLE}",
                   page_icon="💸", layout="wide")

st.title("💸 Money Flow")
st.caption("See every dollar from gross paycheck down to grocery bill.")


# -----------------------------------------------------------------------------
# Sidebar — filters and display options
# -----------------------------------------------------------------------------
# Pull available months from both data sources for the filter
months_available = run_query("""
    SELECT DISTINCT year_month FROM (
        SELECT year_month FROM finance.silver.everydollar_transactions
        UNION
        SELECT date_format(check_date, 'yyyy-MM') AS year_month
        FROM finance.silver.paycheck_totals
    )
    WHERE year_month IS NOT NULL
    ORDER BY year_month DESC
""")["year_month"].tolist()

with st.sidebar:
    st.subheader("🎛️ Display Options")

    time_mode = st.radio(
        "Time range",
        ["All time", "By month"],
        help="View aggregate totals or filter by specific months",
    )

    selected_months = months_available  # default
    if time_mode == "By month":
        selected_months = st.multiselect(
            "Months to include",
            options=months_available,
            default=months_available[:1] if months_available else [],
            help="Select one or more months",
        )

    st.divider()
    show_levels = st.multiselect(
        "Sankey detail levels",
        options=[1, 2, 3],
        default=[1, 2, 3],
        help="1 = paycheck breakdown · 2 = spending groups · 3 = items",
    )

    st.divider()
    st.caption(
        "**Level 1**: Gross Pay → Taxes, Deductions, Take-Home\n\n"
        "**Level 2**: Take-Home → Category Groups\n\n"
        "**Level 3**: Category Groups → Items"
    )


if not show_levels:
    st.warning("Pick at least one Sankey level in the sidebar.")
    st.stop()

if time_mode == "By month" and not selected_months:
    st.warning("Pick at least one month in the sidebar.")
    st.stop()


# -----------------------------------------------------------------------------
# Build filter conditions — used by every query below
# -----------------------------------------------------------------------------
if time_mode == "All time":
    everydollar_where = "WHERE flow_category = 'expense'"
    payroll_where     = ""
    title_suffix      = "All Time"
else:
    months_list = ",".join(f"'{m}'" for m in selected_months)
    everydollar_where = (
        f"WHERE flow_category = 'expense' AND year_month IN ({months_list})"
    )
    payroll_where = (
        f"WHERE date_format(check_date, 'yyyy-MM') IN ({months_list})"
    )
    title_suffix = (selected_months[0] if len(selected_months) == 1
                    else f"{len(selected_months)} months selected")


# -----------------------------------------------------------------------------
# Build the Sankey data dynamically based on filters
# -----------------------------------------------------------------------------
sankey_parts = []

# LEVEL 1: Gross Pay → Taxes, Deductions, Take-Home
if 1 in show_levels:
    sankey_parts.append(f"""
        SELECT 'Gross Pay' AS source_node, description AS target_node,
               ROUND(SUM(amount), 2) AS amount, 1 AS level
        FROM finance.silver.paycheck_employee_taxes
        {payroll_where}
        GROUP BY description

        UNION ALL

        SELECT 'Gross Pay', description, ROUND(SUM(amount), 2), 1
        FROM finance.silver.paycheck_pre_tax_deductions
        {payroll_where}
        GROUP BY description

        UNION ALL

        SELECT 'Gross Pay', description, ROUND(SUM(amount), 2), 1
        FROM finance.silver.paycheck_post_tax_deductions
        {payroll_where}
        GROUP BY description

        UNION ALL

        SELECT 'Gross Pay', 'Take-Home', ROUND(SUM(net_pay), 2), 1
        FROM finance.silver.paycheck_totals
        {payroll_where}
    """)

# LEVEL 2: Take-Home → Category Groups
if 2 in show_levels:
    sankey_parts.append(f"""
        SELECT 'Take-Home' AS source_node, category_group AS target_node,
               ROUND(SUM(amount_abs), 2) AS amount, 2 AS level
        FROM finance.silver.everydollar_transactions
        {everydollar_where}
        GROUP BY category_group
    """)

# LEVEL 3: Category Group → Category Item
if 3 in show_levels:
    sankey_parts.append(f"""
        SELECT category_group AS source_node, category_item AS target_node,
               ROUND(SUM(amount_abs), 2) AS amount, 3 AS level
        FROM finance.silver.everydollar_transactions
        {everydollar_where}
        GROUP BY category_group, category_item
    """)

if sankey_parts:
    full_query = "\nUNION ALL\n".join(sankey_parts)
    sankey_df = run_query(f"""
        SELECT * FROM ({full_query})
        WHERE amount > 0
        ORDER BY level, amount DESC
    """)
else:
    sankey_df = pd.DataFrame(columns=["source_node", "target_node", "amount", "level"])


# -----------------------------------------------------------------------------
# THE SANKEY
# -----------------------------------------------------------------------------
st.markdown(f"### 🌊 Money Flow — {title_suffix}")

if sankey_df.empty:
    st.info("No data for the selected filters. Try different months or levels.")
else:
    st.plotly_chart(
        sankey_money_flow(sankey_df, height=700),
        use_container_width=True,
    )

st.divider()


# -----------------------------------------------------------------------------
# Waterfall — gross to net (and optionally to spending)
# -----------------------------------------------------------------------------
st.subheader(f"💧 Waterfall: Gross Pay Breakdown — {title_suffix}")
st.caption(
    "Visualizes the countdown from gross pay through every deduction to "
    "your bank account."
)

# Get totals filtered by selected months
paycheck_totals = run_query(f"""
    SELECT
        SUM(gross_pay)           AS gross,
        SUM(employee_taxes)      AS taxes,
        SUM(pre_tax_deductions)  AS pretax,
        SUM(post_tax_deductions) AS posttax,
        SUM(net_pay)             AS net
    FROM finance.silver.paycheck_totals
    {payroll_where}
""")

if paycheck_totals.empty or paycheck_totals["gross"].iloc[0] is None:
    st.info("No paycheck data for the selected months.")
    st.stop()

# Deduction breakdowns (filtered)
tax_breakdown = run_query(f"""
    SELECT description, SUM(amount) AS amount
    FROM finance.silver.paycheck_employee_taxes
    {payroll_where}
    GROUP BY description ORDER BY amount DESC
""")

pretax_breakdown = run_query(f"""
    SELECT description, SUM(amount) AS amount
    FROM finance.silver.paycheck_pre_tax_deductions
    {payroll_where}
    GROUP BY description ORDER BY amount DESC
""")

posttax_breakdown = run_query(f"""
    SELECT description, SUM(amount) AS amount
    FROM finance.silver.paycheck_post_tax_deductions
    {payroll_where}
    GROUP BY description ORDER BY amount DESC
""")

# Spending by category group (filtered)
spending_by_group = run_query(f"""
    SELECT category_group, SUM(amount_abs) AS amount
    FROM finance.silver.everydollar_transactions
    {everydollar_where}
    GROUP BY category_group ORDER BY amount DESC
""")


detail_mode = st.radio(
    "Detail level",
    ["Grouped (summary)", "Detailed (every deduction)"],
    horizontal=True,
)

gross = float(paycheck_totals["gross"].iloc[0])

if detail_mode == "Grouped (summary)":
    deductions = [
        ("Taxes",          float(paycheck_totals["taxes"].iloc[0] or 0)),
        ("Pre-Tax Ded.",   float(paycheck_totals["pretax"].iloc[0] or 0)),
        ("Post-Tax Ded.",  float(paycheck_totals["posttax"].iloc[0] or 0)),
    ]
else:
    deductions = (
        [(r["description"], float(r["amount"])) for _, r in tax_breakdown.iterrows()]
      + [(r["description"], float(r["amount"])) for _, r in pretax_breakdown.iterrows()]
      + [(r["description"], float(r["amount"])) for _, r in posttax_breakdown.iterrows()]
    )

include_spending = st.checkbox(
    "Continue waterfall through spending categories",
    value=False,
    help="Adds your tracked expenses. Will go negative if spending exceeds "
         "paycheck data for the selected period.",
)

spending = None
if include_spending and not spending_by_group.empty:
    spending = [(r["category_group"], float(r["amount"]))
                for _, r in spending_by_group.iterrows()]

st.plotly_chart(
    waterfall_gross_to_net(gross, deductions, spending, height=600),
    use_container_width=True,
)


# -----------------------------------------------------------------------------
# Summary metrics
# -----------------------------------------------------------------------------
st.divider()
st.subheader(f"📊 Summary — {title_suffix}")

t = paycheck_totals.iloc[0]
total_ded = float(t["taxes"] or 0) + float(t["pretax"] or 0) + float(t["posttax"] or 0)
effective_rate = (total_ded / float(t["gross"])) * 100 if t["gross"] else 0
take_home_rate = (float(t["net"]) / float(t["gross"])) * 100 if t["gross"] else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Gross",       money(t["gross"]))
c2.metric("Total Deductions",  money(total_ded), f"{effective_rate:.1f}% of gross")
c3.metric("Total Take-Home",   money(t["net"]),  f"{take_home_rate:.1f}% of gross")
c4.metric("Paychecks", int(run_query(f"""
    SELECT COUNT(DISTINCT check_date) AS n
    FROM finance.silver.paycheck_totals {payroll_where}
""")["n"].iloc[0]))
