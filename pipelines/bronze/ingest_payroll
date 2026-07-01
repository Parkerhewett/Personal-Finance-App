# Cell 1
%pip install openpyxl

# Cell 2
dbutils.library.restartPython()

# =============================================================================
# Ingest Workday Payslip XLSX → finance.bronze.payroll_raw
# Source: /Volumes/finance/raw/payroll_files/*.xlsx
# Idempotent: re-running replaces rows from any file that's re-uploaded.
# Output: long-format table — one row per (section, description) line item.
# =============================================================================

import os
import pandas as pd
from pyspark.sql import functions as F

VOLUME_PATH  = "/Volumes/finance/raw/payroll_files"
TARGET_TABLE = "finance.bronze.payroll_raw"

# Section markers as they appear in column 0 of the payslip
SECTION_MARKERS = {
    "Current and YTD Totals":   "totals",
    "Earnings":                 "earnings",
    "Employee Taxes":           "employee_taxes",
    "Pre Tax Deductions":       "pre_tax_deductions",
    "Post Tax Deductions":      "post_tax_deductions",
    "Employer Paid Benefits":   "employer_paid_benefits",
    "Taxable Wages":            "taxable_wages",
    "Withholding":              "withholding",
    "Payment Information":      "payment_information",
}

# ---------- helpers -------------------------------------------------------
def _to_decimal(val):
    """Robust money-string → float. Returns None if not parseable."""
    if val is None or pd.isna(val) or str(val).strip() == "":
        return None
    s = str(val).strip().replace("$", "").replace(",", "")
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return None

def _extract_meta(rows):
    """Pull employee_id, pay periods, check date from Payslip Information block."""
    meta = {k: None for k in
            ["employee_id", "pay_period_begin", "pay_period_end",
             "check_date", "check_number"]}
    for i, row in enumerate(rows):
        if str(row[0]).strip() == "Payslip Information":
            headers = [str(c).strip() for c in rows[i + 1]]
            values  = [str(c).strip() for c in rows[i + 2]]
            m = dict(zip(headers, values))
            meta["employee_id"]      = m.get("Employee ID")
            meta["pay_period_begin"] = m.get("Pay Period Begin")
            meta["pay_period_end"]   = m.get("Pay Period End")
            meta["check_date"]       = m.get("Check Date")
            meta["check_number"]     = m.get("Check Number")
            break
    return meta

def _parse_totals(sub_headers, data_rows, meta):
    """Special handling: pivot Current/YTD rows into one record per metric."""
    current, ytd = {}, {}
    for r in data_rows:
        m = dict(zip(sub_headers, r))
        label = m.get("Balance Period", "").strip()
        if   label == "Current": current = m
        elif label == "YTD":     ytd     = m
    out = []
    for col in sub_headers:
        if col in ("Balance Period", ""): continue
        out.append({**meta,
            "section": "totals",
            "description": col,
            "amount": _to_decimal(current.get(col)),
            "ytd":    _to_decimal(ytd.get(col)),
            "hours": None, "rate": None, "dates": None,
            "account_name": None, "account_number": None,
            "raw_payload": None,
        })
    return out

def _parse_generic(section, sub_headers, data_rows, meta):
    """Default parser for sections with Description + Amount + YTD layout."""
    out = []
    for r in data_rows:
        m = {h: v for h, v in zip(sub_headers, r) if h}
        # Description fallback chain across section types
        desc = (m.get("Description") or m.get("Bank") or
                m.get("Balance Period") or list(m.values())[0])
        out.append({**meta,
            "section": section,
            "description": desc,
            "amount": _to_decimal(m.get("Amount") or m.get("Amount in Pay Group Currency")),
            "ytd":    _to_decimal(m.get("YTD")),
            "hours":  _to_decimal(m.get("Hours") or m.get("Hours Worked")),
            "rate":   _to_decimal(m.get("Rate")),
            "dates":  m.get("Dates"),
            "account_name": m.get("Account Name"),      # for payment_information
            "account_number": m.get("Account Number"),  # for payment_information
            "raw_payload": str(m),   # preserve all extra fields for silver
        })
    return out

# ---------- main parser ---------------------------------------------------
def parse_payslip(file_path):
    df = pd.read_excel(file_path, sheet_name=0, header=None, dtype=str).fillna("")
    rows = df.values.tolist()
    # pad ragged rows
    width = max(len(r) for r in rows)
    rows = [list(r) + [""] * (width - len(r)) for r in rows]

    meta = _extract_meta(rows)
    records = []
    i = 0
    while i < len(rows):
        first = str(rows[i][0]).strip()
        if first in SECTION_MARKERS:
            section     = SECTION_MARKERS[first]
            sub_headers = [str(c).strip() for c in rows[i + 1]]
            j = i + 2
            data_rows = []
            while j < len(rows):
                if str(rows[j][0]).strip() in SECTION_MARKERS: break
                if all(str(c).strip() == "" for c in rows[j]):
                    j += 1; continue
                data_rows.append([str(c).strip() for c in rows[j]])
                j += 1
            if section == "totals":
                records += _parse_totals(sub_headers, data_rows, meta)
            else:
                records += _parse_generic(section, sub_headers, data_rows, meta)
            i = j
        else:
            i += 1
    return records

# ---------- driver --------------------------------------------------------
def ingest_all():
    files = [f for f in os.listdir(VOLUME_PATH) if f.lower().endswith(".xlsx")]
    if not files:
        print("⚠️  No .xlsx payslips found.")
        return

    all_recs = []
    for fname in files:
        fpath = os.path.join(VOLUME_PATH, fname)
        recs = parse_payslip(fpath)
        for r in recs: r["source_file"] = fname
        all_recs.extend(recs)
        print(f"✅ {fname}: {len(recs)} records")

    if not all_recs: return

    sdf = (spark.createDataFrame(pd.DataFrame(all_recs))
        .withColumns({
            "pay_period_begin": F.to_date("pay_period_begin", "MM/dd/yyyy"),
            "pay_period_end":   F.to_date("pay_period_end",   "MM/dd/yyyy"),
            "check_date":       F.to_date("check_date",       "MM/dd/yyyy"),
            "amount":           F.col("amount").cast("decimal(12,2)"),
            "ytd":              F.col("ytd").cast("decimal(14,2)"),
            "hours":            F.col("hours").cast("decimal(8,2)"),
            "rate":             F.col("rate").cast("decimal(10,4)"),
            "ingest_ts":        F.current_timestamp()
        }))

    if not spark.catalog.tableExists(TARGET_TABLE):
        sdf.write.format("delta").saveAsTable(TARGET_TABLE)
    else:
        files_in_batch = [r.source_file for r in sdf.select("source_file").distinct().collect()]
        in_list = ",".join([f"'{f}'" for f in files_in_batch])
        spark.sql(f"DELETE FROM {TARGET_TABLE} WHERE source_file IN ({in_list})")
        sdf.write.format("delta").mode("append").saveAsTable(TARGET_TABLE)

    print(f"✅ Loaded {sdf.count()} rows into {TARGET_TABLE}")
    display(spark.table(TARGET_TABLE)
            .orderBy(F.desc("check_date"), "section", "description")
            .limit(40))

ingest_all()
