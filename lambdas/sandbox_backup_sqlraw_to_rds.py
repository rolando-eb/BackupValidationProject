import json
import datetime
import pyodbc
import psycopg2
import psycopg2.extras

# ------------------------------
# SQL Server connection info
# ------------------------------
SQL_SERVER   = "DBMONPLAS2"
SQL_DB       = "DBAdmin"
SQL_USER     = "backup_reader_poc"
SQL_PASSWORD = "Strong!_OnlyForPOC"
SQL_PORT     = 1433

# ------------------------------
# PostgreSQL connection info
# ------------------------------
PG_HOST     = "dbmonplas2-pgsql-public.cqfjvur03nbh.us-west-2.rds.amazonaws.com"
PG_DB       = "dbmonplas2pgsql"
PG_USER     = "postgres"
PG_PASSWORD = "sqladmin"   # TODO: move to secrets manager later
PG_PORT     = 5432

# ------------------------------
# SQL Server Query - Today Only
# ------------------------------
QUERY = r"""
SELECT
    BackupRawId,
    SourceServer,
    DatabaseName,
    BackupType,
    BackupStartDate,
    BackupFinishDate,
    CompressedSizeBytes,
    PhysicalDeviceName
FROM [DBAdmin].[dbo].[ProdBackup_Raw]
WHERE SourceServer = 'LAWLDBP1LAS1'
  AND DatabaseName = 'lawprod'
  AND BackupType IN ('D','I')     -- Full and Diff only
  AND CAST(BackupStartDate AS DATE)
      IN (CAST(GETDATE() AS DATE),
          CAST(DATEADD(DAY, -1, GETDATE()) AS DATE))
ORDER BY BackupStartDate DESC;
"""

def get_sql_connection():
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={SQL_SERVER},{SQL_PORT};"
        f"DATABASE={SQL_DB};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=10;"
    )
    return pyodbc.connect(conn_str)

def fetch_sql_rows():
    rows = []
    conn = get_sql_connection()
    cursor = conn.cursor()
    cursor.execute(QUERY)
    cols = [col[0] for col in cursor.description]
    for r in cursor.fetchall():
        rows.append(dict(zip(cols, r)))
    return rows

# ------------------------------
# PostgreSQL helpers
# ------------------------------

def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
        port=PG_PORT,
    )

UPSERT_SQL = """
INSERT INTO rds_backup_check.backup_raw_onprem (
    backup_raw_id,
    source_server,
    database_name,
    backup_type,
    backup_start_utc,
    backup_finish_utc,
    backup_size_bytes,
    physical_filename
)
VALUES (
    %(backup_raw_id)s,
    %(source_server)s,
    %(database_name)s,
    %(backup_type)s,
    %(backup_start_utc)s,
    %(backup_finish_utc)s,
    %(backup_size_bytes)s,
    %(physical_filename)s
)
ON CONFLICT (backup_raw_id)
DO UPDATE SET
    source_server     = EXCLUDED.source_server,
    database_name     = EXCLUDED.database_name,
    backup_type       = EXCLUDED.backup_type,
    backup_start_utc  = EXCLUDED.backup_start_utc,
    backup_finish_utc = EXCLUDED.backup_finish_utc,
    backup_size_bytes = EXCLUDED.backup_size_bytes,
    physical_filename = EXCLUDED.physical_filename;
"""

def upsert_backup_row(pg_conn, row):
    data = {
        "backup_raw_id":     row["BackupRawId"],
        "source_server":     row["SourceServer"],
        "database_name":     row["DatabaseName"],
        "backup_type":       row["BackupType"],
        "backup_start_utc":  row["BackupStartDate"],
        "backup_finish_utc": row["BackupFinishDate"],
        "backup_size_bytes": row["CompressedSizeBytes"],  # FIXED HERE
        "physical_filename": row["PhysicalDeviceName"],
    }

    with pg_conn.cursor() as cur:
        cur.execute(UPSERT_SQL, data)

# ------------------------------
# Lambda handler (local + cloud)
# ------------------------------

def lambda_handler(event, context):
    ts = datetime.datetime.utcnow().isoformat() + "Z"

    try:
        sql_rows = fetch_sql_rows()
        print(f"Retrieved {len(sql_rows)} rows from SQL Server (today only).")

        if not sql_rows:
            return {
                "status": "ok",
                "message": "No rows returned for today.",
                "queried_at_utc": ts
            }

        pg_conn = get_pg_connection()

        inserted = 0
        for row in sql_rows:
            upsert_backup_row(pg_conn, row)
            inserted += 1

        pg_conn.commit()
        pg_conn.close()

        return {
            "status": "ok",
            "queried_at_utc": ts,
            "rows_processed": inserted,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }