# Personal Finance Analytics Platform

A personal finance analytics platform built on **Databricks, Delta Lake, SQL, Python, and Streamlit** using a **Medallion Architecture (Bronze → Silver → Gold)** data model.

This project was created to provide visibility into cash flow, spending habits, paycheck details, savings rates, and net worth growth while also serving as a hands-on learning project for Databricks data engineering and analytics workflows. The application combines budgeting data from EveryDollar exports with payroll data from Workday payslips and presents the results through an interactive Streamlit dashboard.
***

# Features

* Automated ingestion of EveryDollar transaction exports
* Payroll processing from Workday payslip files
* Bronze, Silver, and Gold Databricks data layers
* Spending analysis and category trends
* Sankey diagrams showing money flow
* Paycheck reconciliation between payroll and budgeting data
* Savings rate calculations
* Net worth tracking
* Future net worth forecasting using regression and exponential growth models
* Interactive Streamlit dashboard for visualization and exploration

***

# Architecture

```text
Workday Payslips and Everydollar Transactions (CSV)
        │
        ▼
 Bronze Layer
        │
        ▼
 Silver Layer
        │
        ▼
  Gold Layer
        │
        ▼
 Streamlit Dashboard
```

***

# Repository Structure

```text
setup/
├── 00_setup.sql
├── 00_setup2.sql
├── net_worth_gold.sql

pipelines/
├── bronze/
├── silver/
└── gold/

app/
├── app.py
└── pages/

utils/
```

***

# Setup Layer

The **setup** folder contains SQL scripts used to create the Databricks catalogs, schemas, and supporting objects required for the application.

It also contains the net worth Gold-layer views that provide:

* Current account balances
* Net worth summaries
* Historical net worth calculations
* Account categorization
* Growth trend datasets

These objects support the Net Worth section of the dashboard and enable long-term financial tracking. 
***

# Bronze Layer

The Bronze layer ingests raw source data with minimal transformation.

## Payroll Ingestion

Payroll data originates from exported **Workday payslip files**.

Workday exports contain multiple sections including:

* Earnings
* Taxes
* Pre-tax deductions
* Post-tax deductions
* Employer benefits
* Payment information
* Year-to-date totals

Because the payroll files are structured report exports rather than traditional tabular datasets, custom parsing logic was developed to identify section headers and normalize the information into a consistent Bronze table.

## Budget Data Ingestion

Budgeting data is sourced from **EveryDollar transaction exports**.

During development, EveryDollar changed the structure of its CSV export files by introducing additional columns not present in the original dataset.

To maintain compatibility with historical exports while supporting new downloads, ingestion logic was adapted to handle both formats. Although relatively minor, this became a good real-world example of dealing with source-system schema drift during ETL development.

***

# Silver Layer

The Silver layer applies cleansing, standardization, and enrichment logic to the raw data.

Examples include:

### Payroll

* Payroll totals pivoted into a reporting-friendly structure
* Separate tables for:
  * Earnings
  * Taxes
  * Pre-tax deductions
  * Post-tax deductions
  * Employer contributions
  * Payment distributions

### Budget Transactions

* Merchant name normalization
* Transfer detection
* Flow categorization
* Date dimensions
* Transaction keys
* Paycheck deposit identification

These transformations create a reusable data foundation for reporting and analytics.
***

# Gold Layer

The Gold layer contains business-ready analytical datasets used by the dashboard.

Gold models power:

### Cash Flow Analytics

Monthly summaries of:

* Income
* Expenses
* Transfers
* Cash flow trends

### Spending Analytics

* Spending by category
* Spending by merchant
* Monthly trends
* Category contribution percentages

### Payroll Analytics

* Gross-to-net breakdowns
* Deduction tracking
* Savings rate calculations
* Employer contribution analysis

### Paycheck Reconciliation

A reconciliation process compares payroll deposits against recorded EveryDollar income transactions, helping identify missing or incorrectly recorded paycheck entries.

### Net Worth Tracking

The application includes a custom net worth tracking system.

Users can manually enter account balance snapshots directly through the Streamlit application. These snapshots are stored in Databricks tables and used to calculate:

* Current net worth
* Historical net worth
* Asset allocation
* Account balances
* Growth over time

The dashboard also includes predictive projections using both:

* Linear regression models
* Exponential growth models

to estimate potential future net worth based on historical trends.

***

# Dashboard Screenshots

## Home Dashboard

images/home_page.png

***

## Money Flow Analysis

> *Insert Sankey Diagram screenshot here*

images/money\_flow\.png

***

## Spending Analysis

> *Insert Spending Dashboard screenshot here*

images/spending\_dashboard.png

***

## Paycheck Analytics

> *Insert Paycheck Dashboard screenshot here*

images/paycheck\_dashboard.png

***

## Net Worth Tracking

> *Insert Net Worth Dashboard screenshot here*

images/networth\_dashboard.png

***

# Technology Stack

* Databricks
* Delta Lake
* SQL
* Python
* PySpark
* Streamlit
* Plotly
* Pandas

***

# Future Enhancements

* Automated bank connectivity
* Investment performance tracking
* Budget vs actual analysis
* Goal tracking
* Enhanced forecasting models
* Additional financial health metrics

***

# Why I Built This

This project started as a personal finance tool but evolved into a way to learn and apply modern data engineering concepts using Databricks.

The goal was to build a complete end-to-end solution that combines data ingestion, transformation, analytics, and visualization while solving a real-world problem: understanding where money comes from, where it goes, and how it impacts long-term financial growth.
