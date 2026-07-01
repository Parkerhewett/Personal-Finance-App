-- -----------------------------------------------------------------------------
-- 5. NET WORTH TABLES
-- -----------------------------------------------------------------------------

-- Account registry — one row per account you want to track
CREATE TABLE IF NOT EXISTS finance.silver.account_definitions (
    account_id     STRING NOT NULL,
    name           STRING NOT NULL,
    account_type   STRING NOT NULL,  -- checking, savings, retirement, hsa, investment, cash, liability
    institution    STRING,
    is_active      BOOLEAN,
    display_order  INT,
    created_at     TIMESTAMP,
    notes          STRING
) USING DELTA
COMMENT 'Master list of tracked accounts for net worth calculation.';

-- Snapshot history — append-only balance entries
CREATE TABLE IF NOT EXISTS finance.bronze.balance_snapshots (
    snapshot_id    STRING NOT NULL,
    account_id     STRING NOT NULL,
    snapshot_date  DATE NOT NULL,
    balance        DECIMAL(14,2) NOT NULL,
    note           STRING,
    entered_at     TIMESTAMP
) USING DELTA
COMMENT 'Manual balance snapshots — one row per (account, snapshot date).';

-- Seed your accounts (run once — uses MERGE so re-running is safe)
MERGE INTO finance.silver.account_definitions AS t
USING (
    SELECT * FROM VALUES
        ('chk_local',    'Bank',  'checking',   'bank 2',       2, 'Secondary checking'),
        ('chk_usaa',     'Bank',        'checking',   'bank 1',             1, 'Primary checking'),
        ('sav_hysa',     'Bank',   'savings',    'Saving',              3, 'HYSA'),
        ('ret_401k',     'Bank)',               'retirement', 'plan',    4, 'Employer match + employee'),
        ('ret_roth_ira', 'Roth',             'retirement', 'Trust',     5, 'Bi-monthly contribution'),
        ('hsa_main',     'HSA',                  'hsa',        'plan',    6, 'Triple tax advantaged')
    AS t (account_id, name, account_type, institution, display_order, notes)
) AS s
ON t.account_id = s.account_id
WHEN NOT MATCHED THEN INSERT (account_id, name, account_type, institution, display_order, notes)
                       VALUES (s.account_id, s.name, s.account_type, s.institution, s.display_order, s.notes);
