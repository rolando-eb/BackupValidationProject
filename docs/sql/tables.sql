create database dbmonplas2pgsql;

 --dbmonplas2pgsql

CREATE TABLE backup_raw_onprem (
    backup_raw_id        BIGINT PRIMARY KEY,
    source_server        VARCHAR(128) NOT NULL,
    database_name        VARCHAR(128) NOT NULL,
    backup_type          VARCHAR(10) NOT NULL,   -- FULL, DIFF, LOG
    backup_start_utc     TIMESTAMPTZ NOT NULL,
    backup_finish_utc    TIMESTAMPTZ NOT NULL,
    backup_size_bytes    BIGINT,
    physical_filename    VARCHAR(1024) NOT NULL,
    s3_expected_filename VARCHAR(512) GENERATED ALWAYS AS (
        LOWER(source_server || '_' || database_name || '_' || backup_type || '_' ||
              TO_CHAR(backup_start_utc, 'YYYYMMDD_HH24MISS'))
    ) STORED
);

--TABLE 2
-- Table: rds_backup_check.s3_backup_inventory

-- DROP TABLE IF EXISTS rds_backup_check.s3_backup_inventory;

CREATE TABLE IF NOT EXISTS rds_backup_check.s3_backup_inventory
(
    s3_id bigint NOT NULL DEFAULT nextval('rds_backup_check.s3_backup_inventory_s3_id_seq'::regclass),
    bucket_name character varying(128) COLLATE pg_catalog."default" NOT NULL,
    file_key character varying(2048) COLLATE pg_catalog."default" NOT NULL,
    file_name character varying(512) COLLATE pg_catalog."default" NOT NULL,
    file_extension character varying(10) COLLATE pg_catalog."default" NOT NULL,
    file_size_bytes bigint,
    last_modified_utc timestamp with time zone NOT NULL,
    parsed_server character varying(256) COLLATE pg_catalog."default",
    parsed_database character varying(256) COLLATE pg_catalog."default",
    parsed_type character varying(10) COLLATE pg_catalog."default",
    parsed_date date,
    parsed_time time without time zone,
    parsed_timestamp_utc timestamp with time zone,
    import_utc timestamp with time zone DEFAULT now(),
    unique_hash bytea NOT NULL,
    is_deleted boolean DEFAULT false,
    CONSTRAINT s3_backup_inventory_pkey PRIMARY KEY (s3_id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS rds_backup_check.s3_backup_inventory
    OWNER to postgres;
-- Index: idx_s3_parsed_db_date

-- DROP INDEX IF EXISTS rds_backup_check.idx_s3_parsed_db_date;

CREATE INDEX IF NOT EXISTS idx_s3_parsed_db_date
    ON rds_backup_check.s3_backup_inventory USING btree
    (parsed_database COLLATE pg_catalog."default" ASC NULLS LAST, parsed_timestamp_utc ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;
-- Index: ux_s3_backup_hash

-- DROP INDEX IF EXISTS rds_backup_check.ux_s3_backup_hash;

CREATE UNIQUE INDEX IF NOT EXISTS ux_s3_backup_hash
    ON rds_backup_check.s3_backup_inventory USING btree
    (unique_hash ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;

--Table 3
-- Table: rds_backup_check.backup_delivery_status

-- DROP TABLE IF EXISTS rds_backup_check.backup_delivery_status;

CREATE TABLE IF NOT EXISTS rds_backup_check.backup_delivery_status
(
    backup_raw_id bigint NOT NULL,
    onprem_backup_timestamp timestamp with time zone NOT NULL,
    s3_arrival_timestamp timestamp with time zone,
    s3_id bigint,
    delivery_status character varying(32) COLLATE pg_catalog."default" NOT NULL,
    notes character varying(2000) COLLATE pg_catalog."default",
    updated_utc timestamp with time zone DEFAULT now(),
    CONSTRAINT backup_delivery_status_pkey PRIMARY KEY (backup_raw_id),
    CONSTRAINT backup_delivery_status_backup_raw_id_fkey FOREIGN KEY (backup_raw_id)
        REFERENCES rds_backup_check.backup_raw_onprem (backup_raw_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT backup_delivery_status_s3_id_fkey FOREIGN KEY (s3_id)
        REFERENCES rds_backup_check.s3_backup_inventory (s3_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS rds_backup_check.backup_delivery_status
    OWNER to postgres;
-- Index: idx_delivery_status_state

-- DROP INDEX IF EXISTS rds_backup_check.idx_delivery_status_state;

CREATE INDEX IF NOT EXISTS idx_delivery_status_state
    ON rds_backup_check.backup_delivery_status USING btree
    (delivery_status COLLATE pg_catalog."default" ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;