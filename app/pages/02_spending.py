"""Spending Analysis page."""

import streamlit as st
import pandas as pd

from utils.config import GOLD, APP_TITLE
from utils.db import run_query
from utils.charts import horizontal_bar_categories, monthly_trend, donut_chart
from utils.formatting import money, pct

st.set_page_config(page_title=f"Spending · {APP_TITLE}",
                   page_icon="📊", layout="wide")

st.title("📊 Spending Analysis")
st.caption("Where the money goes — by category, by month, by merchant.")


# -----------------------------------------------------------------------------
# Sidebar filters
# -----------------------------------------------------------------------------
months_available = run_query(f"""
    SELECT DISTINCT year_month
    FROM {GOLD['spending_by_category']}
    ORDER BY year_month DESC
""")["year_month"].tolist()

with st.sidebar:
    st.subheader("🎛️ Filters")
    selected_months = st.multiselect(
        "Months to include",
        options=months_available,
        default=months_available,
    )

if not selected_months:
    st.warning("Pick at least one month in the sidebar.")
    st.stop()

months_in = ",".join(f"'{m}'" for m in selected_months)


# -----------------------------------------------------------------------------
# KPI row
# -----------------------------------------------------------------------------
kpis = run_query(f"""
    SELECT
        SUM(total_spent)              AS total,
        AVG(total_spent)              AS avg_category,
        COUNT(DISTINCT year_month)    AS months,
        COUNT(DISTINCT category_item) AS unique_items,
        SUM(transaction_count)        AS txns
    FROM {GOLD['spending_by_category']}
    WHERE year_month IN ({months_in})
""")
k = kpis.iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Spent",     money(k["total"]))
c2.metric("Monthly Average", money(float(k["total"]) / max(int(k["months"]), 1)))
c3.metric("Transactions",    f"{int(k['txns']):,}")
c4.metric("Unique Categories", int(k["unique_items"]))

st.divider()


# -----------------------------------------------------------------------------
# Spending by category group — donut + table
# -----------------------------------------------------------------------------
st.subheader("🍩 By Category Group")
col1, col2 = st.columns([1, 1])

group_totals = run_query(f"""
    SELECT category_group, SUM(total_spent) AS total_spent
    FROM {GOLD['spending_by_category']}
    WHERE year_month IN ({months_in})
    GROUP BY category_group
    ORDER BY total_spent DESC
""")

with col1:
    st.plotly_chart(
        donut_chart(group_totals, "category_group", "total_spent",
                    title="Spending Mix"),
        use_container_width=True,
    )

with col2:
    display_df = group_totals.copy()
    display_df["pct"] = display_df["total_spent"] / display_df["total_spent"].sum() * 100
    display_df["total_spent"] = display_df["total_spent"].apply(money)
    display_df["pct"]         = display_df["pct"].apply(lambda x: f"{x:.1f}%")
    display_df.columns = ["Category Group", "Total Spent", "% of Total"]
    st.dataframe(display_df, hide_index=True, use_container_width=True)

st.divider()


# -----------------------------------------------------------------------------
# Top categories (horizontal bar)
# -----------------------------------------------------------------------------
st.subheader("🏆 Top Spending Categories")

top_n = st.slider("Show top N categories", 5, 25, 15)

top_items = run_query(f"""
    SELECT category_group, category_item, SUM(total_spent) AS total_spent
    FROM {GOLD['spending_by_category']}
    WHERE year_month IN ({months_in})
    GROUP BY category_group, category_item
    ORDER BY total_spent DESC
    LIMIT {top_n}
""")

st.plotly_chart(
    horizontal_bar_categories(
        top_items, "category_item", "total_spent",
        color_col="category_group",
        title=f"Top {top_n} Categories",
        height=max(400, 25 * top_n),
    ),
    use_container_width=True,
)

st.divider()


# -----------------------------------------------------------------------------
# Month-over-month trend
# -----------------------------------------------------------------------------
st.subheader("📈 Month-Over-Month Trend")

trend_df = run_query(f"""
    SELECT year_month, category_group, SUM(total_spent) AS total_spent
    FROM {GOLD['spending_by_category']}
    WHERE year_month IN ({months_in})
    GROUP BY year_month, category_group
    ORDER BY year_month, category_group
""")

st.plotly_chart(
    monthly_trend(trend_df, "year_month", "total_spent",
                  color="category_group",
                  title="Spending by Category Over Time"),
    use_container_width=True,
)


# -----------------------------------------------------------------------------
# Detailed table
# -----------------------------------------------------------------------------
with st.expander("🔬 Detailed breakdown — every category every month"):
    detail = run_query(f"""
        SELECT year_month, category_group, category_item,
               transaction_count, total_spent, pct_of_month
        FROM {GOLD['spending_by_category']}
        WHERE year_month IN ({months_in})
        ORDER BY year_month DESC, total_spent DESC
    """)
    st.dataframe(detail, hide_index=True, use_container_width=True)
