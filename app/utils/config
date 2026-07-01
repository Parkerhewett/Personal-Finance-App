"""App-wide configuration constants."""

# -----------------------------------------------------------------------------
# Catalog / schema names — change here if you ever rename
# -----------------------------------------------------------------------------
CATALOG = "finance"

SCHEMAS = {
    "bronze": f"{CATALOG}.bronze",
    "silver": f"{CATALOG}.silver",
    "gold":   f"{CATALOG}.gold",
}

# -----------------------------------------------------------------------------
# Gold table references — single source of truth for table names
# -----------------------------------------------------------------------------
GOLD = {
    "monthly_cashflow":        f"{CATALOG}.gold.monthly_cashflow",
    "spending_by_category":    f"{CATALOG}.gold.spending_by_category",
    "paycheck_breakdown":      f"{CATALOG}.gold.paycheck_breakdown",
    "paycheck_reconciliation": f"{CATALOG}.gold.paycheck_reconciliation",
    "sankey_flows":            f"{CATALOG}.gold.sankey_flows",
    "savings_rate":            f"{CATALOG}.gold.savings_rate",
}

# Add to the existing GOLD dict
GOLD["net_worth_current"]  = f"{CATALOG}.gold.net_worth_current"
GOLD["net_worth_summary"]  = f"{CATALOG}.gold.net_worth_summary"
GOLD["net_worth_history"]  = f"{CATALOG}.gold.net_worth_history"

# New: silver/bronze refs we'll need for writes
ACCOUNTS_TABLE  = f"{CATALOG}.silver.account_definitions"
SNAPSHOTS_TABLE = f"{CATALOG}.bronze.balance_snapshots"

# -----------------------------------------------------------------------------
# App display settings
# -----------------------------------------------------------------------------
APP_TITLE   = "Personal Finance Dashboard"
APP_ICON    = "💰"
OWNER_NAME  = "Parker"

# Default look-back when no filter is set
DEFAULT_MONTHS_LOOKBACK = 6
