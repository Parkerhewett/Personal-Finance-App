# =============================================================================
# Silver: Payroll — Section-specific tables from bronze.payroll_raw
# Strategy: Full refresh on each run (bronze is source of truth, scale is small)
# Output: 8 section tables in finance.silver schema
# =============================================================================

from pyspark.sql import functions as F
from pyspark.sql.window import Window

BRONZE = "finance.bronze.payroll_raw"

bronze = spark.table(BRONZE)


# -----------------------------------------------------------------------------
# Shared base — common columns we'll carry into every section table
# -----------------------------------------------------------------------------
base_cols = [
    "employee_id",
    "pay_period_begin",
    "pay_period_end",
    "check_date",
    "check_number",
    "source_file",
]


# -----------------------------------------------------------------------------
# 1. paycheck_totals — pivoted wide: one row per check
# -----------------------------------------------------------------------------
# bronze stores totals as long format (one row per metric).
# We pivot to: hours_worked, gross_pay, pre_tax_deductions, employee_taxes,
#              post_tax_deductions, net_pay
totals = (bronze
    .filter(F.col("section") == "totals")
    .groupBy(*base_cols)
    .pivot("description", [
        "Hours Worked", "Gross Pay", "Pre Tax Deductions",
        "Employee Taxes", "Post Tax Deductions", "Net Pay",
    ])
    .agg(F.first("amount"))
    .withColumnRenamed("Hours Worked",        "hours_worked")
    .withColumnRenamed("Gross Pay",           "gross_pay")
    .withColumnRenamed("Pre Tax Deductions",  "pre_tax_deductions")
    .withColumnRenamed("Employee Taxes",      "employee_taxes")
    .withColumnRenamed("Post Tax Deductions", "post_tax_deductions")
    .withColumnRenamed("Net Pay",             "net_pay")
)

# Same pivot for YTD values
totals_ytd = (bronze
    .filter(F.col("section") == "totals")
    .groupBy(*base_cols)
    .pivot("description", [
        "Hours Worked", "Gross Pay", "Pre Tax Deductions",
        "Employee Taxes", "Post Tax Deductions", "Net Pay",
    ])
    .agg(F.first("ytd"))
    .withColumnRenamed("Hours Worked",        "hours_worked_ytd")
    .withColumnRenamed("Gross Pay",           "gross_pay_ytd")
    .withColumnRenamed("Pre Tax Deductions",  "pre_tax_deductions_ytd")
    .withColumnRenamed("Employee Taxes",      "employee_taxes_ytd")
    .withColumnRenamed("Post Tax Deductions", "post_tax_deductions_ytd")
    .withColumnRenamed("Net Pay",             "net_pay_ytd")
)

paycheck_totals = (totals.join(totals_ytd, base_cols, "inner")
    .orderBy("check_date"))

(paycheck_totals.write
    .format("delta").mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("finance.silver.paycheck_totals"))


# -----------------------------------------------------------------------------
# 2-7. Generic section tables — same shape, different filter
# -----------------------------------------------------------------------------
# These sections all share: description, amount, ytd (and earnings adds hours/rate)
def build_section_table(section_name: str, target: str, include_hours_rate=False):
    cols_to_select = base_cols + [
        F.col("description"),
        F.col("amount"),
        F.col("ytd"),
    ]
    if include_hours_rate:
        cols_to_select += [F.col("hours"), F.col("rate"), F.col("dates").alias("date_range")]

    df = (bronze
        .filter(F.col("section") == section_name)
        .select(*cols_to_select)
        .orderBy("check_date", "description"))

    (df.write
        .format("delta").mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(target))

    print(f"✅ {target}: {df.count()} rows")

build_section_table("earnings",              "finance.silver.paycheck_earnings",              include_hours_rate=True)
build_section_table("employee_taxes",        "finance.silver.paycheck_employee_taxes")
build_section_table("pre_tax_deductions",    "finance.silver.paycheck_pre_tax_deductions")
build_section_table("post_tax_deductions",   "finance.silver.paycheck_post_tax_deductions")
build_section_table("employer_paid_benefits","finance.silver.paycheck_employer_benefits")
build_section_table("taxable_wages",         "finance.silver.paycheck_taxable_wages")


# -----------------------------------------------------------------------------
# 8. paycheck_payments — bank deposit splits (special: 'description' is the bank)
# -----------------------------------------------------------------------------
# bronze stored bank in 'description' and account name in raw_payload
# We parse raw_payload to extract Account Name and Account Number cleanly
payments = (bronze
    .filter(F.col("section") == "payment_information")
    .select(
        *base_cols,
        F.col("description").alias("bank"),
        F.regexp_extract("raw_payload",
                         r"'Account Name':\s*'([^']*)'", 1).alias("account_name"),
        F.regexp_extract("raw_payload",
                         r"'Account Number':\s*'([^']*)'", 1).alias("account_number_masked"),
        F.col("amount").alias("deposit_amount"),
    )
    .orderBy("check_date", "bank"))

(payments.write
    .format("delta").mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("finance.silver.paycheck_payments"))

print(f"✅ finance.silver.paycheck_payments: {payments.count()} rows")


# -----------------------------------------------------------------------------
# Sanity check — show what we built
# -----------------------------------------------------------------------------
print("\n=== Paycheck Totals (wide) ===")
display(spark.table("finance.silver.paycheck_totals"))

print("\n=== Paycheck Earnings ===")
display(spark.table("finance.silver.paycheck_earnings"))

print("\n=== Paycheck Payments ===")
display(spark.table("finance.silver.paycheck_payments"))
