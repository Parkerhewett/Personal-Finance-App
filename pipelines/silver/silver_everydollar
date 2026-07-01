# =============================================================================
# Silver: EveryDollar — Cleaned transaction table from bronze.everydollar_raw
# Strategy: Full refresh (small dataset, idempotent re-runs)
# Output: finance.silver.everydollar_transactions (single enriched table)
# =============================================================================

from pyspark.sql import functions as F

BRONZE = "finance.bronze.everydollar_raw"
TARGET = "finance.silver.everydollar_transactions"

bronze = spark.table(BRONZE)


# -----------------------------------------------------------------------------
# Step 1: Normalize sign convention
# -----------------------------------------------------------------------------
# EveryDollar uses:  positive = money in,  negative = money out
# We'll keep `amount` signed for math, add `amount_abs` for visualizations,
# and add a `direction` column ('inflow' / 'outflow') for easy filtering.
cleaned = (bronze
    .withColumn("amount_abs", F.abs(F.col("amount")))
    .withColumn("direction",
        F.when(F.col("amount") > 0, F.lit("inflow"))
         .when(F.col("amount") < 0, F.lit("outflow"))
         .otherwise(F.lit("zero")))
)


# -----------------------------------------------------------------------------
# Step 2: Flag internal transfers (the +X / -X pairs in 'fund' type)
# -----------------------------------------------------------------------------
# These are money moving between your own accounts — not real income/expense.
# We keep them in the table for audit, but flag them so dashboards can exclude.
cleaned = cleaned.withColumn(
    "is_transfer",
    F.when(F.col("transaction_type") == "fund", F.lit(True))
     .otherwise(F.lit(False))
)


# -----------------------------------------------------------------------------
# Step 3: Derive a unified high-level flow category
# -----------------------------------------------------------------------------
# Groups every row into one of: income | expense | transfer
# This is what your Sankey diagram and KPI cards will pivot on.
cleaned = cleaned.withColumn(
    "flow_category",
    F.when(F.col("is_transfer"), F.lit("transfer"))
     .when(F.col("transaction_type") == "income", F.lit("income"))
     .when(F.col("transaction_type") == "expense", F.lit("expense"))
     .otherwise(F.lit("other"))
)


# -----------------------------------------------------------------------------
# Step 4: Add time dimensions
# -----------------------------------------------------------------------------
# These columns make GROUP BY queries trivial throughout silver/gold/dashboards.
cleaned = (cleaned
    .withColumn("year",         F.year("transaction_date"))
    .withColumn("month",         F.month("transaction_date"))
    .withColumn("year_month",    F.date_format("transaction_date", "yyyy-MM"))
    .withColumn("week_of_year",  F.weekofyear("transaction_date"))
    .withColumn("day_of_week",   F.date_format("transaction_date", "EEEE"))
    .withColumn("day_of_month",  F.dayofmonth("transaction_date"))
)


# -----------------------------------------------------------------------------
# Step 5: Lightly clean merchant names
# -----------------------------------------------------------------------------
# - Trim whitespace
# - Collapse multiple spaces
# - Title-case ALL CAPS merchants for readability (preserves mixed case)
# - Strip trailing "Tulsa OK" / state codes that add noise
cleaned = (cleaned
    .withColumn("merchant_clean",
        F.regexp_replace(F.col("merchant"), r"\s+", " "))    # collapse spaces
    .withColumn("merchant_clean", F.trim("merchant_clean"))
    .withColumn("merchant_clean",
        F.regexp_replace("merchant_clean",
            r"\s+(Tulsa|Norman|Oklahoma City|Oklahoma Cityok)\s*(OK)?$", ""))
    .withColumn("merchant_clean",
        F.regexp_replace("merchant_clean", r"\s+\*+\s*\w*$", ""))  # remove **** suffixes
)


# -----------------------------------------------------------------------------
# Step 6: Identify paycheck deposits (for reconciliation with payroll data)
# -----------------------------------------------------------------------------
# EveryDollar labels them "Paycheck 1" / "Paycheck 2" — useful link to payroll
cleaned = cleaned.withColumn(
    "is_paycheck_deposit",
    F.when(
        (F.col("category_group") == "Income") &
        F.col("category_item").rlike(r"^Paycheck \d+$"),
        F.lit(True)
    ).otherwise(F.lit(False))
)


# -----------------------------------------------------------------------------
# Step 7: Add a stable surrogate row key
# -----------------------------------------------------------------------------
# Useful when you want to point at a specific transaction from a dashboard,
# join from notes, or troubleshoot duplicates. Hash of natural keys.
cleaned = cleaned.withColumn(
    "transaction_key",
    F.sha2(F.concat_ws("||",
        F.col("transaction_date").cast("string"),
        F.col("category_group"),
        F.col("category_item"),
        F.col("merchant"),
        F.col("amount").cast("string"),
        F.col("source_file"),
    ), 256)
)


# -----------------------------------------------------------------------------
# Step 8: Final column ordering + write
# -----------------------------------------------------------------------------
final = cleaned.select(
    "transaction_key",
    "transaction_date",
    "year",
    "month",
    "year_month",
    "week_of_year",
    "day_of_week",
    "day_of_month",
    "category_group",
    "category_item",
    "transaction_type",
    "flow_category",
    "direction",
    "is_transfer",
    "is_paycheck_deposit",
    F.col("merchant").alias("merchant_raw"),
    "merchant_clean",
    "amount",       # signed
    "amount_abs",   # absolute value
    "note",
    "source_file",
    "ingest_ts",
).orderBy(F.desc("transaction_date"), "category_group")

(final.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TARGET))

print(f"✅ {TARGET}: {final.count()} rows")


# -----------------------------------------------------------------------------
# Sanity checks
# -----------------------------------------------------------------------------
print("\n=== Monthly flow summary ===")
display(spark.sql(f"""
    SELECT
        year_month,
        flow_category,
        COUNT(*)               AS txn_count,
        ROUND(SUM(amount_abs),2) AS total_abs
    FROM {TARGET}
    GROUP BY year_month, flow_category
    ORDER BY year_month, flow_category
"""))

print("\n=== Top spending categories (current data) ===")
display(spark.sql(f"""
    SELECT
        category_group,
        category_item,
        COUNT(*)               AS txn_count,
        ROUND(SUM(amount_abs),2) AS total_spent
    FROM {TARGET}
    WHERE flow_category = 'expense'
    GROUP BY category_group, category_item
    ORDER BY total_spent DESC
    LIMIT 15
"""))

print("\n=== Paycheck deposits (will reconcile with payroll later) ===")
display(spark.sql(f"""
    SELECT transaction_date, category_item, merchant_clean, amount
    FROM {TARGET}
    WHERE is_paycheck_deposit = true
    ORDER BY transaction_date
"""))
