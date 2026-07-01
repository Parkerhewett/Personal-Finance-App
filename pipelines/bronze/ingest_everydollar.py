# =============================================================================
# Ingest EveryDollar Transaction CSVs → finance.bronze.everydollar_raw
# Source: /Volumes/finance/raw/budgeting_files/*.csv
# Idempotent: re-running replaces rows from any file that's re-uploaded.
# NOTE: Automatically detects old format (7 cols) vs new format (8 cols with Account)
# =============================================================================

from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType
import csv

VOLUME_PATH  = "[PATH]"
TARGET_TABLE = "[TABLE]"

# Dynamically detect which files have which format by reading headers
files = dbutils.fs.ls(VOLUME_PATH)
csv_files = [f.name for f in files if f.name.endswith('.csv')]

old_format_files = []
new_format_files = []

print("Detecting file formats...")
for fname in csv_files:
    fpath = f"{VOLUME_PATH}/{fname}"
    with open(fpath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        num_cols = len(header)
        
        if num_cols == 7:  # Old format: Group,Item,Type,Date,Merchant,Amount,Note
            old_format_files.append(fname)
            print(f"  {fname}: OLD format (7 cols)")
        elif num_cols == 8:  # New format: Group,Item,Type,Date,Merchant,Account,Amount,Note
            new_format_files.append(fname)
            print(f"  {fname}: NEW format (8 cols)")
        else:
            print(f"  WARNING: {fname} has {num_cols} columns - skipping!")

# Process OLD format files (7 columns)
if old_format_files:
    old_file_paths = [f"{VOLUME_PATH}/{f}" for f in old_format_files]
    raw_old = (spark.read
        .option("header", "true")
        .option("inferSchema", "false")
        .option("quote", '"')
        .option("escape", '"')
        .csv(old_file_paths)
        .withColumn("source_file", F.regexp_extract(F.col("_metadata.file_path"), r"[^/]+$", 0))
        .withColumn("Account", F.lit(None).cast(StringType()))  # Add null Account column
    )
else:
    # Create empty DataFrame with expected schema if no old files
    raw_old = spark.createDataFrame([], StructType([
        StructField("Group", StringType(), True),
        StructField("Item", StringType(), True),
        StructField("Type", StringType(), True),
        StructField("Date", StringType(), True),
        StructField("Merchant", StringType(), True),
        StructField("Amount", StringType(), True),
        StructField("Note", StringType(), True),
        StructField("source_file", StringType(), True),
        StructField("Account", StringType(), True)
    ]))

# Process NEW format files (8 columns)
if new_format_files:
    new_file_paths = [f"{VOLUME_PATH}/{f}" for f in new_format_files]
    raw_new = (spark.read
        .option("header", "true")
        .option("inferSchema", "false")
        .option("quote", '"')
        .option("escape", '"')
        .csv(new_file_paths)
        .withColumn("source_file", F.regexp_extract(F.col("_metadata.file_path"), r"[^/]+$", 0))
    )
else:
    # Create empty DataFrame with expected schema if no new files
    raw_new = spark.createDataFrame([], StructType([
        StructField("Group", StringType(), True),
        StructField("Item", StringType(), True),
        StructField("Type", StringType(), True),
        StructField("Date", StringType(), True),
        StructField("Merchant", StringType(), True),
        StructField("Account", StringType(), True),
        StructField("Amount", StringType(), True),
        StructField("Note", StringType(), True),
        StructField("source_file", StringType(), True)
    ]))

# Union both datasets - now they have the same columns
raw = raw_old.unionByName(raw_new)

# Clean + cast
clean = (raw
    .withColumn("transaction_date", F.to_date("Date", "MM/dd/yyyy"))
    .withColumn("amount",           F.col("Amount").cast("decimal(12,2)"))
    .withColumn("ingest_ts",        F.current_timestamp())
    .select(
        F.col("Group").alias("category_group"),
        F.col("Item").alias("category_item"),
        F.col("Type").alias("transaction_type"),
        "transaction_date",
        F.col("Merchant").alias("merchant"),
        F.col("Account").alias("account"),  # Properly aligned for both formats
        "amount",
        F.col("Note").alias("note"),
        "source_file",
        "ingest_ts",
    ))

# Idempotent write: delete-by-source-file, then append
if not spark.catalog.tableExists(TARGET_TABLE):
    clean.write.format("delta").saveAsTable(TARGET_TABLE)
else:
    # Check if account column exists in the table; if not, add it
    existing_cols = [col.name for col in spark.table(TARGET_TABLE).schema]
    if "account" not in existing_cols:
        print("Adding 'account' column to existing table...")
        spark.sql(f"ALTER TABLE {TARGET_TABLE} ADD COLUMN account STRING AFTER merchant")
    
    # Delete existing rows from files in this batch
    files_in_batch = [r.source_file for r in clean.select("source_file").distinct().collect()]
    if files_in_batch:
        in_list = ",".join([f"'{f}'" for f in files_in_batch])
        spark.sql(f"DELETE FROM {TARGET_TABLE} WHERE source_file IN ({in_list})")
    
    # Append new data
    clean.write.format("delta").mode("append").saveAsTable(TARGET_TABLE)

print(f"\nIngested {clean.count()} rows from {len(old_format_files) + len(new_format_files)} files")
print(f"  Old format: {len(old_format_files)} files")
print(f"  New format: {len(new_format_files)} files")
display(clean.groupBy("source_file", "account").count().orderBy("source_file"))
display(spark.table(TARGET_TABLE).orderBy(F.desc("transaction_date")).limit(20))
