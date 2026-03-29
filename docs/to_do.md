Recommended next step
Create a specific user:
CREATE USER backup_loader WITH PASSWORD 'xxxxx';
GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA rds_backup_check TO backup_loader;

-----------------------------------

