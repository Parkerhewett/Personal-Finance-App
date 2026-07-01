# =============================================================================
# Gold Layer — Analytics tables for the Streamlit finance dashboard
# Strategy: Full refresh (small data, derived from silver)
# Output: 6 gold tables in finance.gold schema
# =============================================================================

from pyspark.sql import functions as F

# -----------------------------------------------------------------------------
# 1. gold.monthly_cashflow — the headline numbers
# -----------------------------------------------------------------------------
# One row per (month, flow_category) with totals.
# Excludes transfers so income/expense are clean.
spark.sql("""
CREATE OR REPLACE TABLE finance.gold.monthly_cashflow AS
SELECT
    year_month,
    year,
    month,
    flow_category,
    COUNT(*)                            AS transaction_count,
    ROUND(SUM(amount_abs), 2)           AS total_amount,
    ROUND(AVG(amount_abs), 2)           AS avg_transaction,
    ROUND(MAX(amount_abs), 2)           AS max_transaction,
    COUNT(DISTINCT category_item)       AS unique_categories
FROM finance.silver.everydollar_transactions
WHERE is_transfer = false
GROUP BY year_month, year, month, flow_category
ORDER BY year_month, flow_category
""")
print("✅ gold.monthly_cashflow")


# -----------------------------------------------------------------------------
# 2. gold.spending_by_category — for category drilldowns
# -----------------------------------------------------------------------------
spark.sql("""
CREATE OR REPLACE TABLE finance.gold.spending_by_category AS
SELECT
    year_month,
    year,
    month,
    category_group,
    category_item,
    COUNT(*)                                            AS transaction_count,
    ROUND(SUM(amount_abs), 2)                           AS total_spent,
    ROUND(AVG(amount_abs), 2)                           AS avg_transaction,
    -- % of month's total expense going to this category
    ROUND(SUM(amount_abs) * 100.0 / SUM(SUM(amount_abs))
          OVER (PARTITION BY year_month), 2)            AS pct_of_month
FROM finance.silver.everydollar_transactions
WHERE flow_category = 'expense'
GROUP BY year_month, year, month, category_group, category_item
ORDER BY year_month, total_spent DESC
""")
print("✅ gold.spending_by_category")


# -----------------------------------------------------------------------------
# 3. gold.paycheck_breakdown — long format paycheck composition
# -----------------------------------------------------------------------------
# Unions all the paycheck dollar flows into one long table.
# Perfect source for stacked bar charts and Sankey middle layer.
# Buckets: gross → taxes → pre-tax deductions → post-tax deductions → net
spark.sql("""
CREATE OR REPLACE TABLE finance.gold.paycheck_breakdown AS

-- Gross pay
SELECT
    check_date,
    'gross_pay'      AS bucket,
    'Gross Pay'      AS bucket_label,
    'Gross'          AS bucket_group,
    gross_pay        AS amount
FROM finance.silver.paycheck_totals

UNION ALL

-- Individual employee taxes
SELECT
    check_date,
    'tax_' || lower(replace(description, ' ', '_')) AS bucket,
    description                                     AS bucket_label,
    'Employee Taxes'                                AS bucket_group,
    amount
FROM finance.silver.paycheck_employee_taxes

UNION ALL

-- Individual pre-tax deductions
SELECT
    check_date,
    'pretax_' || lower(replace(description, ' ', '_')) AS bucket,
    description                                        AS bucket_label,
    'Pre-Tax Deductions'                               AS bucket_group,
    amount
FROM finance.silver.paycheck_pre_tax_deductions

UNION ALL

-- Individual post-tax deductions
SELECT
    check_date,
    'posttax_' || lower(replace(description, ' ', '_')) AS bucket,
    description                                         AS bucket_label,
    'Post-Tax Deductions'                               AS bucket_group,
    amount
FROM finance.silver.paycheck_post_tax_deductions

UNION ALL

-- Bank deposits (net pay split)
SELECT
    check_date,
    'deposit_' || lower(replace(bank, ' ', '_')) AS bucket,
    bank                                         AS bucket_label,
    'Net Deposits'                               AS bucket_group,
    deposit_amount                               AS amount
FROM finance.silver.paycheck_payments

UNION ALL

-- Employer contributions (don't count toward net but matter for total comp)
SELECT
    check_date,
    'employer_' || lower(replace(description, ' ', '_')) AS bucket,
    description                                          AS bucket_label,
    'Employer Benefits'                                  AS bucket_group,
    amount
FROM finance.silver.paycheck_employer_benefits

ORDER BY check_date, bucket_group, bucket
""")
print("✅ gold.paycheck_breakdown")


# -----------------------------------------------------------------------------
# 4. gold.paycheck_reconciliation — does budget match actual paychecks?
# -----------------------------------------------------------------------------
# For each paycheck, compare:
#   1. Budgeted deposits (excludes Roth IRA and other non-budgeted accounts)
#   2. What EveryDollar recorded as paycheck income within +/- 5 days
# Roth IRA deposits are excluded because they're automatic savings, not budgeted income.
spark.sql("""
CREATE OR REPLACE TABLE finance.gold.paycheck_reconciliation AS
WITH payroll AS (
    SELECT
        check_date,
        gross_pay,
        net_pay,
        pre_tax_deductions,
        employee_taxes,
        post_tax_deductions
    FROM finance.silver.paycheck_totals
),
budgeted_deposits AS (
    -- Only deposits that should appear in EveryDollar (excludes Roth IRA)
    SELECT
        check_date,
        SUM(deposit_amount) AS budgeted_total
    FROM finance.silver.paycheck_payments
    WHERE LOWER(account_name) NOT LIKE '%roth ira%'
    GROUP BY check_date
),
roth_deposits AS (
    -- Track Roth IRA separately (for visibility, not reconciliation)
    SELECT
        check_date,
        SUM(deposit_amount) AS roth_ira_amount
    FROM finance.silver.paycheck_payments
    WHERE LOWER(account_name) LIKE '%roth ira%'
    GROUP BY check_date
),
everydollar_income AS (
    SELECT
        transaction_date,
        SUM(amount) AS budgeted_income
    FROM finance.silver.everydollar_transactions
    WHERE is_paycheck_deposit = true
    GROUP BY transaction_date
),
matched AS (
    -- Match budgeted deposits to EveryDollar income within ±5 days
    SELECT
        p.check_date,
        p.gross_pay,
        p.net_pay,
        p.pre_tax_deductions,
        p.employee_taxes,
        p.post_tax_deductions,
        COALESCE(d.budgeted_total, 0) AS budgeted_deposits,
        COALESCE(r.roth_ira_amount, 0) AS roth_ira_deposit,
        SUM(e.budgeted_income) AS everydollar_income_near_check
    FROM payroll p
    LEFT JOIN budgeted_deposits d ON p.check_date = d.check_date
    LEFT JOIN roth_deposits r ON p.check_date = r.check_date
    LEFT JOIN everydollar_income e
        ON e.transaction_date BETWEEN date_sub(p.check_date, 5)
                                  AND date_add(p.check_date, 5)
    GROUP BY p.check_date, p.gross_pay, p.net_pay,
             p.pre_tax_deductions, p.employee_taxes, p.post_tax_deductions,
             d.budgeted_total, r.roth_ira_amount
)
SELECT
    check_date,
    gross_pay,
    net_pay,
    budgeted_deposits,
    roth_ira_deposit,
    pre_tax_deductions,
    employee_taxes,
    post_tax_deductions,
    everydollar_income_near_check,
    ROUND(budgeted_deposits - COALESCE(everydollar_income_near_check, 0), 2) AS variance,
    CASE
        WHEN everydollar_income_near_check IS NULL                           THEN 'MISSING in EveryDollar'
        WHEN ABS(budgeted_deposits - everydollar_income_near_check) < 1.00   THEN 'MATCH'
        WHEN ABS(budgeted_deposits - everydollar_income_near_check) < 50.00  THEN 'Minor variance'
        ELSE 'INVESTIGATE'
    END AS status
FROM matched
ORDER BY check_date
""")
print("✅ gold.paycheck_reconciliation")


# -----------------------------------------------------------------------------
# 5. gold.sankey_flows — THE STAR ⭐ source table for the Sankey diagram
# -----------------------------------------------------------------------------
# Builds a 3-level flow:
#   Level 1: Gross Pay → [Taxes, Pre-Tax, Post-Tax, Take-Home]
#   Level 2: Take-Home → spending category groups (Food, Housing, etc.)
#   Level 3: Spending Groups → category items (Groceries, Restaurants, etc.)
#
# Each row: (source_node, target_node, amount, level)
spark.sql("""
CREATE OR REPLACE TABLE finance.gold.sankey_flows AS

-- LEVEL 1A: Gross Pay → Employee Taxes (aggregate per tax type)
SELECT
    'Gross Pay'                                  AS source_node,
    description                                  AS target_node,
    ROUND(SUM(amount), 2)                        AS amount,
    1                                            AS level,
    'paycheck'                                   AS flow_type,
    MIN(check_date)                              AS first_date,
    MAX(check_date)                              AS last_date
FROM finance.silver.paycheck_employee_taxes
GROUP BY description

UNION ALL

-- LEVEL 1B: Gross Pay → Pre-Tax Deductions
SELECT
    'Gross Pay'                                  AS source_node,
    description                                  AS target_node,
    ROUND(SUM(amount), 2)                        AS amount,
    1                                            AS level,
    'paycheck'                                   AS flow_type,
    MIN(check_date), MAX(check_date)
FROM finance.silver.paycheck_pre_tax_deductions
GROUP BY description

UNION ALL

-- LEVEL 1C: Gross Pay → Post-Tax Deductions
SELECT
    'Gross Pay'                                  AS source_node,
    description                                  AS target_node,
    ROUND(SUM(amount), 2)                        AS amount,
    1                                            AS level,
    'paycheck'                                   AS flow_type,
    MIN(check_date), MAX(check_date)
FROM finance.silver.paycheck_post_tax_deductions
GROUP BY description

UNION ALL

-- LEVEL 1D: Gross Pay → Take-Home (Net Pay) ⭐ bridge to spending
SELECT
    'Gross Pay'                                  AS source_node,
    'Take-Home'                                  AS target_node,
    ROUND(SUM(net_pay), 2)                       AS amount,
    1                                            AS level,
    'paycheck'                                   AS flow_type,
    MIN(check_date), MAX(check_date)
FROM finance.silver.paycheck_totals

UNION ALL

-- LEVEL 2: Take-Home → Spending Groups (Housing, Food, Transportation, etc.)
SELECT
    'Take-Home'                                  AS source_node,
    category_group                               AS target_node,
    ROUND(SUM(amount_abs), 2)                    AS amount,
    2                                            AS level,
    'spending'                                   AS flow_type,
    MIN(transaction_date), MAX(transaction_date)
FROM finance.silver.everydollar_transactions
WHERE flow_category = 'expense'
GROUP BY category_group

UNION ALL

-- LEVEL 3: Category Group → Category Item (Food → Groceries, Restaurants, etc.)
SELECT
    category_group                               AS source_node,
    category_item                                AS target_node,
    ROUND(SUM(amount_abs), 2)                    AS amount,
    3                                            AS level,
    'spending'                                   AS flow_type,
    MIN(transaction_date), MAX(transaction_date)
FROM finance.silver.everydollar_transactions
WHERE flow_category = 'expense'
GROUP BY category_group, category_item
""")
print("✅ gold.sankey_flows")


# -----------------------------------------------------------------------------
# 6. gold.savings_rate — % of gross going to retirement/HSA per check
# -----------------------------------------------------------------------------
spark.sql("""
CREATE OR REPLACE TABLE finance.gold.savings_rate AS
WITH retirement_contributions AS (
    SELECT check_date, SUM(amount) AS pretax_retirement
    FROM finance.silver.paycheck_pre_tax_deductions
    WHERE description IN ('401(k) Pre-tax', 'Health Savings Account-employee (HHSAEE)')
    GROUP BY check_date
),
post_tax_retirement AS (
    SELECT check_date, SUM(amount) AS posttax_retirement
    FROM finance.silver.paycheck_post_tax_deductions
    WHERE description IN ('401(k) Roth')
    GROUP BY check_date
),
roth_ira_deposits AS (
    -- Bank deposits going to the Roth IRA account count too
    SELECT check_date, SUM(deposit_amount) AS roth_ira
    FROM finance.silver.paycheck_payments
    WHERE LOWER(account_name) LIKE '%roth ira%'
    GROUP BY check_date
),
employer AS (
    SELECT check_date, SUM(amount) AS employer_match
    FROM finance.silver.paycheck_employer_benefits
    GROUP BY check_date
)
SELECT
    t.check_date,
    date_format(t.check_date, 'yyyy-MM')                AS year_month,
    t.gross_pay,
    t.net_pay,
    COALESCE(r.pretax_retirement, 0)                    AS pretax_savings,
    COALESCE(p.posttax_retirement, 0)                   AS posttax_savings,
    COALESCE(ri.roth_ira, 0)                            AS roth_ira_deposit,
    COALESCE(e.employer_match, 0)                       AS employer_contributions,
    -- Employee-only savings rate (your contributions / gross)
    ROUND(
        (COALESCE(r.pretax_retirement, 0)
         + COALESCE(p.posttax_retirement, 0)
         + COALESCE(ri.roth_ira, 0)
        ) * 100.0 / NULLIF(t.gross_pay, 0), 2)         AS savings_rate_pct,
    -- Total savings rate including employer match
    ROUND(
        (COALESCE(r.pretax_retirement, 0)
         + COALESCE(p.posttax_retirement, 0)
         + COALESCE(ri.roth_ira, 0)
         + COALESCE(e.employer_match, 0)
        ) * 100.0 / NULLIF(t.gross_pay, 0), 2)         AS total_savings_rate_pct
FROM finance.silver.paycheck_totals t
LEFT JOIN retirement_contributions r ON t.check_date = r.check_date
LEFT JOIN post_tax_retirement      p ON t.check_date = p.check_date
LEFT JOIN roth_ira_deposits       ri ON t.check_date = ri.check_date
LEFT JOIN employer                 e ON t.check_date = e.check_date
ORDER BY t.check_date
""")
print("✅ gold.savings_rate")


# -----------------------------------------------------------------------------
# Sanity checks — show each gold table
# -----------------------------------------------------------------------------
print("\n=== Monthly Cashflow ===")
display(spark.table("finance.gold.monthly_cashflow"))

print("\n=== Spending by Category (top 15) ===")
display(spark.sql("SELECT * FROM finance.gold.spending_by_category LIMIT 15"))

print("\n=== Paycheck Reconciliation ===")
display(spark.table("finance.gold.paycheck_reconciliation"))

print("\n=== Sankey Flows ===")
display(spark.sql("""
    SELECT level, source_node, target_node, amount
    FROM finance.gold.sankey_flows
    ORDER BY level, amount DESC
"""))

print("\n=== Savings Rate ===")
display(spark.table("finance.gold.savings_rate"))
