"""Net Worth tracker — manual balance entries and trend visualization."""

import uuid
from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils.config import GOLD, ACCOUNTS_TABLE, SNAPSHOTS_TABLE, APP_TITLE
from utils.db import run_query, execute_write
from utils.charts import _apply_theme, THEME, GROUP_COLORS
from utils.formatting import money, pct

st.set_page_config(page_title=f"Net Worth · {APP_TITLE}",
                   page_icon="🏦", layout="wide")

st.title("🏦 Net Worth")
st.caption("Track your account balances over time. Update whenever — monthly is plenty.")


# -----------------------------------------------------------------------------
# Top: current net worth summary
# -----------------------------------------------------------------------------
summary = run_query(f"SELECT * FROM {GOLD['net_worth_summary']}")
s = summary.iloc[0] if not summary.empty else None

if s is None or s["net_worth"] is None:
    st.info("👋 No snapshots yet! Add your first balance entries below to get started.")
else:
    cols = st.columns(5)
    cols[0].metric("Net Worth",      money(s["net_worth"]))
    cols[1].metric("Liquid Cash",    money(s["liquid_cash"]))
    cols[2].metric("Retirement/HSA", money(s["retirement_total"]))
    cols[3].metric("Investments",    money(s["investments"]))
    cols[4].metric("As Of",
        s["latest_snapshot_date"].strftime("%b %d, %Y")
        if s["latest_snapshot_date"] else "—")

st.divider()


# -----------------------------------------------------------------------------
# Current balances per account
# -----------------------------------------------------------------------------
st.subheader("💼 Current Balances by Account")

current = run_query(f"""
    SELECT name, account_type, institution, bucket, balance, as_of_date
    FROM {GOLD['net_worth_current']}
    ORDER BY display_order
""")

if current.empty or current["balance"].isna().all():
    st.warning("No balance data yet. Add a snapshot below 👇")
else:
    display_df = current.copy()
    display_df["balance_fmt"] = display_df["balance"].apply(
        lambda v: money(v) if pd.notna(v) else "— (no snapshot yet)"
    )
    display_df["as_of_date"] = display_df["as_of_date"].astype(str).replace("NaT", "—")
    display_df = display_df[["name", "account_type", "institution",
                             "bucket", "balance_fmt", "as_of_date"]]
    display_df.columns = ["Account", "Type", "Institution",
                          "Bucket", "Latest Balance", "As Of"]
    st.dataframe(display_df, hide_index=True, use_container_width=True)

st.divider()


# -----------------------------------------------------------------------------
# Trend chart with predictive trendlines
# -----------------------------------------------------------------------------
history = run_query(f"SELECT * FROM {GOLD['net_worth_history']} ORDER BY as_of_date")

if len(history) >= 2:
    st.subheader("📈 Net Worth Over Time")
    
    # Calculate total net worth
    history = history.copy()
    
    # Convert as_of_date to datetime (critical for .dt accessor)
    history["as_of_date"] = pd.to_datetime(history["as_of_date"])
    
    # Convert numeric columns to float (database returns Decimal objects)
    history["liquid"] = pd.to_numeric(history["liquid"], errors='coerce')
    history["retirement"] = pd.to_numeric(history["retirement"], errors='coerce')
    history["investments"] = pd.to_numeric(history["investments"], errors='coerce')
    
    history["total_net_worth"] = (
        history["liquid"].fillna(0) + 
        history["retirement"].fillna(0) + 
        history["investments"].fillna(0)
    )
    
    # Prepare data for regression (days since first snapshot)
    history["days_since_start"] = (
        history["as_of_date"] - history["as_of_date"].min()
    ).dt.days.astype(float)
    
    X = history["days_since_start"].values
    y = history["total_net_worth"].values
    
    # UI Controls
    col1, col2 = st.columns([2, 1])
    
    with col1:
        regression_type = st.radio(
            "Trendline Type",
            ["Exponential Growth", "Linear Growth"],
            horizontal=True,
            help="Exponential captures compound growth (typical for investments), linear shows steady growth"
        )
    
    with col2:
        confidence_width = st.slider(
            "Confidence Band Width",
            min_value=5,
            max_value=30,
            value=15,
            step=5,
            format="%d%%",
            help="Wider bands show more uncertainty in predictions"
        )
    
    # Fit the model and generate predictions
    prediction_days = 365  # Predict 1 year into future
    
    if regression_type == "Exponential Growth":
        # Exponential: y = a * e^(b*x)
        # Linearize: ln(y) = ln(a) + b*x
        if np.all(y > 0):  # Ensure all values are positive for log
            log_y = np.log(y)
            coeffs = np.polyfit(X, log_y, 1)
            b, ln_a = coeffs[0], coeffs[1]
            
            # Generate predictions
            max_days = X.max()
            future_days = np.linspace(0, max_days + prediction_days, 200)
            predictions = np.exp(ln_a) * np.exp(b * future_days)
            
            # Calculate residuals in log space for exponential
            fitted_log = coeffs[0] * X + coeffs[1]
            residuals = log_y - fitted_log
            std_error = np.std(residuals)
            
            # With few data points, use a minimum variance based on percentage
            # This ensures bands are visible even with perfect fits
            min_variance = 0.05  # 5% minimum baseline variance
            if len(X) < 5 or std_error < min_variance:
                std_error = max(std_error, min_variance)
            
            # Convert std error back to original scale
            # For exponential, we multiply/divide by exp(std_error)
            # Scale by confidence width slider
            uncertainty_factor = np.exp(std_error * (confidence_width / 15) * 1.5)
            upper_bound = predictions * uncertainty_factor
            lower_bound = predictions / uncertainty_factor
            
            model_label = "Exponential Fit"
        else:
            # Fallback to linear if negative values present
            coeffs = np.polyfit(X, y, 1)
            future_days = np.linspace(0, X.max() + prediction_days, 200)
            predictions = coeffs[0] * future_days + coeffs[1]
            
            # Calculate standard error
            fitted_values = coeffs[0] * X + coeffs[1]
            residuals = y - fitted_values
            std_error = np.std(residuals)
            
            # Use percentage-based minimum for few data points
            avg_value = np.mean(y)
            min_error = avg_value * 0.05  # 5% of average value
            if len(X) < 5 or std_error < min_error:
                std_error = max(std_error, min_error)
            
            # Create confidence bands
            band_width = std_error * (confidence_width / 15) * 2.0
            upper_bound = predictions + band_width
            lower_bound = predictions - band_width
            
            model_label = "Linear Fit (exponential unavailable)"
    else:
        # Linear: y = mx + b
        coeffs = np.polyfit(X, y, 1)
        future_days = np.linspace(0, X.max() + prediction_days, 200)
        predictions = coeffs[0] * future_days + coeffs[1]
        
        # Calculate standard error
        fitted_values = coeffs[0] * X + coeffs[1]
        residuals = y - fitted_values
        std_error = np.std(residuals)
        
        # Use percentage-based minimum for few data points
        avg_value = np.mean(y)
        min_error = avg_value * 0.05  # 5% of average value
        if len(X) < 5 or std_error < min_error:
            std_error = max(std_error, min_error)
        
        # Create confidence bands (wider for future predictions)
        # Scale uncertainty by distance into future
        time_factor = 1 + (future_days - X.max()) / max(X.max(), 1) * 0.5
        time_factor = np.maximum(time_factor, 1)  # Don't reduce historical uncertainty
        
        band_width = std_error * (confidence_width / 15) * 2.0 * time_factor
        upper_bound = predictions + band_width
        lower_bound = predictions - band_width
        
        model_label = "Linear Fit"
    
    # Convert days back to dates
    base_date = history["as_of_date"].min()
    future_dates = [base_date + timedelta(days=int(d)) for d in future_days]
    
    # Create the visualization
    fig = go.Figure()
    
    # Split point for historical vs future
    split_idx = len(history)
    
    # Historical confidence band (draw as a single filled area)
    fig.add_trace(go.Scatter(
        x=list(future_dates[:split_idx]) + list(reversed(future_dates[:split_idx])),
        y=list(upper_bound[:split_idx]) + list(reversed(lower_bound[:split_idx])),
        fill='toself',
        fillcolor='rgba(150, 150, 150, 0.3)',
        line=dict(width=0),
        name=f"Historical Variance (±{confidence_width}%)",
        showlegend=True,
        hoverinfo='skip',
    ))
    
    # Future confidence band (draw as a single filled area)
    fig.add_trace(go.Scatter(
        x=list(future_dates[split_idx-1:]) + list(reversed(future_dates[split_idx-1:])),
        y=list(upper_bound[split_idx-1:]) + list(reversed(lower_bound[split_idx-1:])),
        fill='toself',
        fillcolor='rgba(100, 200, 100, 0.3)',
        line=dict(width=0),
        name=f"Prediction Range (±{confidence_width}%)",
        showlegend=True,
        hoverinfo='skip',
    ))
    
    # Historical trendline
    fig.add_trace(go.Scatter(
        x=future_dates[:split_idx],
        y=predictions[:split_idx],
        mode="lines",
        name=f"{model_label} (Historical)",
        line=dict(color=THEME["savings"], width=2, dash="dot"),
    ))
    
    # Future prediction
    fig.add_trace(go.Scatter(
        x=future_dates[split_idx-1:],
        y=predictions[split_idx-1:],
        mode="lines",
        name=f"Predicted (next 12 mo)",
        line=dict(color=THEME["income"], width=2, dash="dash"),
    ))
    
    # Actual net worth (on top so it's always visible)
    fig.add_trace(go.Scatter(
        x=history["as_of_date"],
        y=history["total_net_worth"],
        mode="lines+markers",
        name="Actual Net Worth",
        line=dict(color=THEME["accent"], width=3),
        marker=dict(size=8),
    ))
    
    fig.update_layout(
        title=f"Net Worth Projection · {model_label}",
        xaxis_title=None,
        yaxis_title="USD",
        hovermode="x unified",
        showlegend=True,
    )
    
    st.plotly_chart(_apply_theme(fig, 500), use_container_width=True)
    
    # Show projection metrics with ranges
    if len(predictions) > 0:
        current_value = history["total_net_worth"].iloc[-1]
        projected_1yr = predictions[-1]
        projected_upper = upper_bound[-1]
        projected_lower = lower_bound[-1]
        
        growth = projected_1yr - current_value
        growth_pct = (growth / current_value * 100) if current_value > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Net Worth", money(current_value))
        col2.metric(
            "Projected (1 year)", 
            money(projected_1yr), 
            delta=money(growth),
            help=f"Range: {money(projected_lower)} to {money(projected_upper)}"
        )
        col3.metric("Annual Growth Rate", f"{growth_pct:.1f}%")
        
        # Show the range explicitly
        st.caption(
            f"**1-Year Projection Range:** "
            f"{money(projected_lower)} (pessimistic) · "
            f"{money(projected_1yr)} (expected) · "
            f"{money(projected_upper)} (optimistic)"
        )
        
else:
    st.info("📊 Trend chart unlocks after you log balances on 2+ different dates.")

st.divider()


# -----------------------------------------------------------------------------
# Add new snapshot — the main entry form
# -----------------------------------------------------------------------------
st.subheader("✍️ Log a Snapshot")
st.caption("Update the balance for one or more accounts as of a specific date.")

accounts = run_query(f"""
    SELECT account_id, name, account_type, institution
    FROM {ACCOUNTS_TABLE}
    WHERE is_active = true
    ORDER BY display_order
""")

if accounts.empty:
    st.warning(
        "⚠️ No accounts configured yet. Scroll down to **⚙️ Manage Accounts** "
        "to add your first account, then come back here to log a snapshot."
    )
else:
    st.caption(f"📋 {len(accounts)} active account(s) ready for input.")

    with st.form("snapshot_form", clear_on_submit=True):
        snap_date = st.date_input("Snapshot date", value=date.today())

        st.markdown("**Enter balances** _(leave at 0 or blank to skip an account)_")

        balance_inputs = {}

        # Render one input per account in a clean two-column layout
        for _, acct in accounts.iterrows():
            row = st.columns([3, 2])
            with row[0]:
                st.markdown(
                    f"**{acct['name']}**  \n"
                    f"<span style='color:#888;font-size:0.85em'>"
                    f"{acct['account_type']} · {acct['institution']}</span>",
                    unsafe_allow_html=True,
                )
            with row[1]:
                balance_inputs[acct["account_id"]] = st.number_input(
                    label=f"Balance for {acct['name']}",
                    min_value=0.0,
                    value=0.0,
                    step=10.0,
                    format="%.2f",
                    label_visibility="collapsed",
                    key=f"bal_{acct['account_id']}",
                )

        note = st.text_input(
            "Note (optional)",
            placeholder="e.g., end of June paycheck, after Roth IRA deposit",
        )

        submitted = st.form_submit_button(
            "💾 Save Snapshots", type="primary", use_container_width=True
        )

        if submitted:
            rows = []
            for acct_id, bal in balance_inputs.items():
                if bal is not None and bal > 0:  # only save non-zero entries
                    snap_id   = str(uuid.uuid4())
                    safe_note = (note or "").replace("'", "''")
                    rows.append(
                        f"('{snap_id}', '{acct_id}', DATE'{snap_date}', "
                        f"{bal}, '{safe_note}')"
                    )

            if not rows:
                st.warning("Enter at least one balance greater than $0 to save.")
            else:
                values_sql = ",\n".join(rows)
                execute_write(f"""
                    INSERT INTO {SNAPSHOTS_TABLE}
                        (snapshot_id, account_id, snapshot_date, balance, note)
                    VALUES {values_sql}
                """)
                st.success(f"✅ Saved {len(rows)} balance snapshot(s) for {snap_date}.")
                st.rerun()


# -----------------------------------------------------------------------------
# Snapshot history (with delete capability)
# -----------------------------------------------------------------------------
with st.expander("📜 Snapshot History"):
    history_detail = run_query(f"""
        SELECT
            s.snapshot_date,
            a.name AS account,
            s.balance,
            s.note,
            s.snapshot_id,
            s.entered_at
        FROM {SNAPSHOTS_TABLE} s
        JOIN {ACCOUNTS_TABLE} a ON a.account_id = s.account_id
        ORDER BY s.snapshot_date DESC, s.entered_at DESC
        LIMIT 200
    """)

    if history_detail.empty:
        st.caption("No snapshots logged yet.")
    else:
        display_hist = history_detail.copy()
        display_hist["balance"] = display_hist["balance"].apply(money)
        st.dataframe(
            display_hist[["snapshot_date", "account", "balance", "note", "entered_at"]],
            hide_index=True, use_container_width=True,
        )

        st.caption("To delete a snapshot, copy its snapshot_id from below and use the form.")

        st.dataframe(history_detail[["snapshot_id", "snapshot_date", "account"]],
                     hide_index=True, use_container_width=True)

        del_id = st.text_input("Snapshot ID to delete")
        if st.button("🗑️ Delete snapshot", type="secondary"):
            if del_id.strip():
                safe_id = del_id.strip().replace("'", "''")
                execute_write(
                    f"DELETE FROM {SNAPSHOTS_TABLE} "
                    f"WHERE snapshot_id = '{safe_id}'"
                )
                st.success("Deleted.")
                st.rerun()


# -----------------------------------------------------------------------------
# Manage accounts
# -----------------------------------------------------------------------------
with st.expander("⚙️ Manage Accounts (add, deactivate)"):
    st.markdown("**Add a new account**")
    with st.form("add_account_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        new_name        = c1.text_input("Account name")
        new_type        = c2.selectbox(
            "Account type",
            ["checking", "savings", "retirement", "hsa",
             "investment", "cash", "liability"],
        )
        new_institution = c1.text_input("Institution")
        new_order       = c2.number_input("Display order", min_value=1, value=99)
        new_notes       = st.text_input("Notes (optional)")

        if st.form_submit_button("➕ Add account"):
            if new_name.strip():
                acct_id  = "acct_" + new_name.lower().replace(" ", "_")[:20]
                acct_id  = "".join(c for c in acct_id if c.isalnum() or c == "_")
                safe_n   = new_name.replace("'", "''")
                safe_i   = (new_institution or "").replace("'", "''")
                safe_nt  = (new_notes or "").replace("'", "''")
                execute_write(f"""
                    INSERT INTO {ACCOUNTS_TABLE}
                        (account_id, name, account_type, institution,
                         is_active, display_order, notes)
                    VALUES ('{acct_id}', '{safe_n}', '{new_type}', '{safe_i}',
                            true, {new_order}, '{safe_nt}')
                """)
                st.success(f"Added {new_name}")
                st.rerun()
            else:
                st.warning("Name is required.")
