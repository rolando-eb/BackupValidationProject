import json
import datetime
import pyodbc

# ------------------------------
# SQL Server connection info
# ------------------------------
SQL_SERVER   = "DBMONPLAS2"
SQL_DB       = "DBAdmin"
SQL_USER     = "backup_reader_poc"
SQL_PASSWORD = "Strong!_OnlyForPOC"
SQL_PORT     = 1433

# ------------------------------
# Your original query
# ------------------------------
QUERY = r"""
SELECT TOP 5
    *
FROM [DBAdmin].[dbo].[ProdBackup_Raw]
WHERE SourceServer = 'LAWLDBP1LAS1'
  AND DatabaseName = 'Lawprod'
  AND BackupType = 'L'
ORDER BY BackupStartDate DESC;
"""

def get_connection():
    """
    Opens a connection to SQL Server using pyodbc + ODBC Driver 18.
    """
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


def test_query(limit_preview=5):
    """
    Runs your LAWPROD/LOG backup query and returns up to N rows.
    """
    rows = []

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(QUERY)

    columns = [col[0] for col in cursor.description]

    for i, r in enumerate(cursor.fetchall()):
        row_dict = dict(zip(columns, r))
        rows.append(row_dict)
        if i + 1 >= limit_preview:
            break

    return rows


def lambda_handler(event, context):
    """
    Local/lambda entrypoint.
    Runs SQL Server query, returns preview.
    """
    try:
        ts = datetime.datetime.utcnow().isoformat() + "Z"
        data = test_query(limit_preview=5)

        preview = []
        for r in data:
            preview.append({
                "BackupRawId": r.get("BackupRawId"),
                "SourceServer": r.get("SourceServer"),
                "DatabaseName": r.get("DatabaseName"),
                "BackupType": r.get("BackupType"),
                "BackupStartDate": str(r.get("BackupStartDate")),
                "BackupFinishDate": str(r.get("BackupFinishDate")),
                "PhysicalDeviceName": r.get("PhysicalDeviceName"),
            })

        return {
            "status": "ok",
            "queried_at_utc": ts,
            "row_sample_count": len(preview),
            "preview": preview
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }