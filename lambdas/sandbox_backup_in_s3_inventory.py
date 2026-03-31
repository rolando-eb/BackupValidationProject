import os
import json
import boto3
import hashlib
from datetime import datetime, timezone
import psycopg2
import psycopg2.extras
import re

# ------------------------------
# DIRECT VARIABLES (NO ENV VARS)
# ------------------------------

# S3 info
S3_BUCKET = "air-gap-sql-backups-668716374871"
S3_PREFIX = "LAWLD8P1LAS1/lawprod/"

# PostgreSQL info
PG_HOST     = "dbmonplas2-pgsql-public.cqfjvur03nbh.us-west-2.rds.amazonaws.com"
PG_DB       = "dbmonplas2pgsql"
PG_USER     = "postgres"
PG_PASSWORD = "sqladmin"
PG_PORT     = 5432

# ------------------------------
# PostgreSQL connection
# ------------------------------
def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
        port=PG_PORT,
    )

# ------------------------------
# Filename Parser (FULL & DIFF)
# Example:
#   lawwfcp2$lwagop1rax1_lawprod_DIFF_20260329_182705.bak
# ------------------------------
FILENAME_REGEX = re.compile(
    r"^(?P<server>[^_]+)_"
    r"(?P<database>[^_]+)_"
    r"(?P<type>FULL|DIFF)_"
    r"(?P<date>\d{8})_"
    r"(?P<time>\d{6})"
    r"\.bak$",
    re.IGNORECASE
)

def parse_filename(file_name: str):
    m = FILENAME_REGEX.match(file_name)
    if not m:
        return None

    gd = m.groupdict()
    dt_str = f"{gd['date']} {gd['time']}"

    parsed_ts_utc = datetime.strptime(dt_str, "%Y%m%d %H%M%S").replace(tzinfo=timezone.utc)

    return {
        "parsed_server": gd["server"],
        "parsed_database": gd["database"],
        "parsed_type": gd["type"].upper(),
        "parsed_date": parsed_ts_utc.date(),
        "parsed_time": parsed_ts_utc.time(),
        "parsed_timestamp_utc": parsed_ts_utc,
    }

# ------------------------------
# Hash generator
# ------------------------------
def compute_hash(bucket, key, size, last_modified):
    text = f"{bucket}|{key}|{size}|{last_modified}"
    return hashlib.sha256(text.encode("utf-8")).digest()

# ------------------------------
# INSERT into s3_backup_inventory
# ------------------------------
UPSERT_SQL = """
INSERT INTO rds_backup_check.s3_backup_inventory (
    bucket_name,
    file_key,
    file_name,
    file_extension,
    file_size_bytes,
    last_modified_utc,
    parsed_server,
    parsed_database,
    parsed_type,
    parsed_date,
    parsed_time,
    parsed_timestamp_utc,
    unique_hash
)
VALUES (
    %(bucket_name)s,
    %(file_key)s,
    %(file_name)s,
    %(file_extension)s,
    %(file_size_bytes)s,
    %(last_modified_utc)s,
    %(parsed_server)s,
    %(parsed_database)s,
    %(parsed_type)s,
    %(parsed_date)s,
    %(parsed_time)s,
    %(parsed_timestamp_utc)s,
    %(unique_hash)s
)
ON CONFLICT (unique_hash) DO NOTHING;
"""

# ------------------------------
# Lambda Handler
# ------------------------------
s3 = boto3.client("s3")

def lambda_handler(event, context):
    inserted = 0
    scanned = 0

    pg_conn = get_pg_connection()
    pg_cur = pg_conn.cursor()

    continuation_token = None

    while True:
        if continuation_token:
            response = s3.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix=S3_PREFIX,
                ContinuationToken=continuation_token
            )
        else:
            response = s3.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix=S3_PREFIX
            )

        contents = response.get("Contents", [])

        for obj in contents:
            key = obj["Key"]
            file_name = os.path.basename(key)

            # Only process .bak files
            if not file_name.lower().endswith(".bak"):
                continue

            scanned += 1

            parsed = parse_filename(file_name)
            if not parsed:
                # Skip files that don’t match FULL/DIFF pattern
                continue

            file_size = obj.get("Size", 0)
            last_mod  = obj["LastModified"]

            unique_hash = compute_hash(S3_BUCKET, key, file_size, last_mod)

            data = {
                "bucket_name": S3_BUCKET,
                "file_key": key,
                "file_name": file_name,
                "file_extension": "bak",
                "file_size_bytes": file_size,
                "last_modified_utc": last_mod,
                "parsed_server": parsed["parsed_server"],
                "parsed_database": parsed["parsed_database"],
                "parsed_type": parsed["parsed_type"],
                "parsed_date": parsed["parsed_date"],
                "parsed_time": parsed["parsed_time"],
                "parsed_timestamp_utc": parsed["parsed_timestamp_utc"],
                "unique_hash": unique_hash
            }

            pg_cur.execute(UPSERT_SQL, data)
            inserted += pg_cur.rowcount

        if response.get("IsTruncated"):
            continuation_token = response["NextContinuationToken"]
        else:
            break

    pg_conn.commit()
    pg_conn.close()

    return {
        "status": "ok",
        "files_scanned": scanned,
        "inserted_into_pg": inserted
    }

# ------------------------------
# Local Test
# ------------------------------
if __name__ == "__main__":
    print(lambda_handler({}, {}))