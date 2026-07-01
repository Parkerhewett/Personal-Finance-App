-- =============================================================================
-- Personal Finance Project — Setup Script
-- Author: Parker Hewett
-- Purpose: Create catalog, schemas, and volumes for the finance data warehouse.
-- Safe to re-run: uses IF NOT EXISTS so existing objects are untouched.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. CATALOG
-- -----------------------------------------------------------------------------
-- The top-level container for all finance-related data.
CREATE CATALOG IF NOT EXISTS finance
  COMMENT 'Personal finance data warehouse — paychecks, budgeting, cashflow analysis.';

USE CATALOG finance;


-- -----------------------------------------------------------------------------
-- 2. SCHEMAS (medallion architecture)
-- -----------------------------------------------------------------------------
-- raw     → landing zone for unprocessed CSV files (via Volume)
-- bronze  → raw tables, minimal transformation, append-only history
-- silver  → cleaned, typed, deduplicated tables
-- gold    → analytical views and aggregates for the Streamlit app

CREATE SCHEMA IF NOT EXISTS finance.raw
  COMMENT 'Landing zone — original CSV files from payroll and EveryDollar.';

CREATE SCHEMA IF NOT EXISTS finance.bronze
  COMMENT 'Raw ingested data — minimal transformation, preserves source format.';

CREATE SCHEMA IF NOT EXISTS finance.silver
  COMMENT 'Cleaned and typed data — deduplicated, normalized columns.';

CREATE SCHEMA IF NOT EXISTS finance.gold
  COMMENT 'Business-level analytics — joined views for dashboards and reporting.';


-- -----------------------------------------------------------------------------
-- 3. VOLUME (file landing zone)
-- -----------------------------------------------------------------------------
-- A managed Volume in the raw schema for dropping CSV files.
-- Subdirectories will be created automatically on first file upload, OR you
-- can pre-create them via the Catalog Explorer UI.
CREATE VOLUME IF NOT EXISTS finance.raw.finance_files
  COMMENT 'CSV landing zone. Subfolders: /payroll, /everydollar';


-- -----------------------------------------------------------------------------
-- 4. VERIFICATION
-- -----------------------------------------------------------------------------
-- These SELECTs let you confirm everything was created (or already existed).
SHOW SCHEMAS IN finance;
SHOW VOLUMES IN finance.raw;
