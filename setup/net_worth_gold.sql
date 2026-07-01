-- LATEST balance per account
CREATE OR REPLACE VIEW finance.gold.net_worth_current AS
WITH latest AS (
    SELECT account_id, snapshot_date, balance,
           ROW_NUMBER() OVER (PARTITION BY account_id
                              ORDER BY snapshot_date DESC, entered_at DESC) AS rn
    FROM finance.bronze.balance_snapshots
)
SELECT
    d.account_id,
    d.name,
    d.account_type,
    d.institution,
    d.display_order,
    l.snapshot_date  AS as_of_date,
    l.balance,
    CASE
        WHEN d.account_type IN ('checking', 'savings', 'cash') THEN 'Liquid'
        WHEN d.account_type IN ('retirement', 'hsa')           THEN 'Retirement/Tax-Advantaged'
        WHEN d.account_type =  'investment'                    THEN 'Investment'
        WHEN d.account_type =  'liability'                     THEN 'Liability'
        ELSE 'Other'
    END AS bucket
FROM finance.silver.account_definitions d
LEFT JOIN latest l ON l.account_id = d.account_id AND l.rn = 1
WHERE d.is_active = true;


-- NET WORTH TOTAL (latest snapshot per account, summed, with liability subtraction)
CREATE OR REPLACE VIEW finance.gold.net_worth_summary AS
SELECT
    SUM(CASE WHEN account_type = 'liability' THEN -balance ELSE balance END) AS net_worth,
    SUM(CASE WHEN bucket = 'Liquid'                     THEN balance ELSE 0 END) AS liquid_cash,
    SUM(CASE WHEN bucket = 'Retirement/Tax-Advantaged'  THEN balance ELSE 0 END) AS retirement_total,
    SUM(CASE WHEN bucket = 'Investment'                 THEN balance ELSE 0 END) AS investments,
    SUM(CASE WHEN bucket = 'Liability'                  THEN balance ELSE 0 END) AS liabilities,
    MAX(as_of_date) AS latest_snapshot_date
FROM finance.gold.net_worth_current;


-- NET WORTH HISTORY — time series for the growth chart
-- For each snapshot date, sum the most-recent-up-to-that-date balance per account
CREATE OR REPLACE VIEW finance.gold.net_worth_history AS
WITH dates AS (
    SELECT DISTINCT snapshot_date FROM finance.bronze.balance_snapshots
),
snapshots_with_carry AS (
    -- For every date × account combo, find the most recent balance on or before that date
    SELECT
        d.snapshot_date AS as_of_date,
        a.account_id,
        a.account_type,
        (SELECT balance
         FROM finance.bronze.balance_snapshots b
         WHERE b.account_id = a.account_id
           AND b.snapshot_date <= d.snapshot_date
         ORDER BY b.snapshot_date DESC, b.entered_at DESC
         LIMIT 1) AS balance
    FROM dates d
    CROSS JOIN finance.silver.account_definitions a
    WHERE a.is_active = true
)
SELECT
    as_of_date,
    SUM(CASE WHEN account_type = 'liability' THEN -balance ELSE balance END) AS net_worth,
    SUM(CASE WHEN account_type IN ('checking','savings','cash') THEN balance ELSE 0 END) AS liquid,
    SUM(CASE WHEN account_type IN ('retirement','hsa')          THEN balance ELSE 0 END) AS retirement,
    SUM(CASE WHEN account_type = 'investment'                   THEN balance ELSE 0 END) AS investments
FROM snapshots_with_carry
WHERE balance IS NOT NULL
GROUP BY as_of_date
ORDER BY as_of_date;
